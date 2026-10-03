# Metodologia — como isso foi descoberto

Registro completo do processo de engenharia reversa, incluindo os caminhos que **não**
funcionaram. Útil pra quem for investigar outro dispositivo Dahua/Imou/Intelbras white-label
parecido, ou pra entender por que certas abordagens "óbvias" foram descartadas.

## Objetivo original

Ler localmente (sem nuvem) os dados do sensor Zigbee Intelbras MTU 1001, pareado via hub MCA
1002, que só é acessível pelo app Mibo.

## Caminhos tentados e descartados

### 1. Root do celular (via fastboot)
Tentado em 3 máquinas diferentes (fox-server, fox-wks Windows, fox-wks CachyOS), 3+ cabos, um
hub USB — o celular nunca entrou em modo fastboot de forma utilizável (erros de enumeração
USB). Abandonado — não é limitação do protocolo, é limitação física do hardware/porta
específicos desse aparelho.

### 2. Vincular a conta no Tuya IoT Platform (método que funcionou pra outro projeto)
O app Mibo não expõe a opção de "escanear QR code" pra vincular a conta a um Cloud Project
Tuya de terceiro (diferente do Smart Life/Tuya Smart genéricos). Mesmo que o hardware por trás
seja Tuya, a Intelbras bloqueia esse caminho de propósito no app white-label.

### 3. `adb backup` (sem root)
Retornou sempre 0 bytes, mesmo confirmando o diálogo na tela do celular. Causa confirmada:
`android:allowBackup="false"` no `AndroidManifest.xml` do app (verificado via `androguard`).

### 4. MITM clássico (proxy HTTP do sistema + mitmproxy)
Funcionou parcialmente: capturou negociação TLS, mas **zero tráfego** da parte Tuya/IoT do app
("Minha casa" dava "Falha ao carregar"). Causa real (achada depois): faltava permissão de
**Localização** pro app — SDKs Tuya/ThingSmart exigem isso silenciosamente, sem nenhum erro
visível, antes de sequer tentar qualquer chamada de rede. Corrigido via
`adb shell pm grant <pkg> android.permission.ACCESS_FINE_LOCATION` (e COARSE).

Mesmo depois de corrigir isso, o MITM clássico (certificado de CA instalado manualmente) não
decifrou o tráfego real do app — certificate pinning nativo (C/C++, não Java) bloqueia.

### 5. PCAPdroid (captura via VPNService, sem root)
Resolveu o problema de visibilidade de rede (viu domínios, IPs, portas), mas sua opção de
decriptação de TLS embutida (MITM local) esbarra no mesmo pinning nativo do item 4 — instalar
o certificado CA do PCAPdroid não foi suficiente.

## O que funcionou

### Passo 1 — Frida Gadget embutido no APK (bypass de pinning Java)

APK é um **split APK** (base + 3 splits por ABI/densidade/locale) — foi necessário mesclar
numa APK única antes de patchar (`APKEditor` da REAndroid, comando `m`/merge).

```bash
java -jar APKEditor.jar m -i <pasta_com_splits> -o merged.apk
objection patchapk -s merged.apk -a arm64-v8a     # injeta libfrida-gadget.so
```

**Cuidado:** `objection patchapk -a arm64` (sem o `-v8a`) gera uma pasta de lib errada
(`lib/arm64` em vez de `lib/arm64-v8a`), o app crasha com
`UnsatisfiedLinkError: library "libfrida-gadget.so" not found`. Descubra o valor certo com
`adb shell getprop ro.product.cpu.abi` e use exatamente esse valor no `-a`.

Depois de instalar o APK com patch (desinstala o original primeiro — assinatura muda, precisa
logar de novo no app), um script Frida universal de bypass (hook em
`com.android.org.conscrypt.TrustManagerImpl.verifyChain`, `SSLContext.init`, etc) passou a
interceptar várias conexões — mas **não decifrou o canal mais importante** (o que carrega os
dados do sensor). Confirma: esse canal específico usa pinning **nativo** (C/C++), não Java.

### Passo 2 — hook nativo em `SSL_read`/`SSL_write` (captura em texto plano, sem quebrar pinning)

Em vez de tentar vencer o pinning pra um proxy MITM funcionar, a virada foi: **não precisa
decifrar o tráfego de rede** — basta ler o buffer de texto plano *dentro do processo do app*,
no ponto exato onde os dados entram/saem da camada TLS. Isso funciona **independente de
pinning**, porque o pinning só valida o certificado do servidor; não impede ler o que o
processo já decidiu confiar.

```js
// localizar a lib de TLS do sistema (resolve sozinho, independente de qual
// codigo nativo do app esta chamando)
var mod = Process.findModuleByName("libssl.so"); // (tambem existe como libjavacrypto.so,
                                                    // mesmo endereco -- e a mesma lib)
var readAddr = mod.findExportByName("SSL_read");
var writeAddr = mod.findExportByName("SSL_write");
```

**Armadilha 1:** `Interceptor.attach` com `onEnter`/`onLeave` funcionou para `onEnter`, mas
`onLeave` **nunca disparou** (a função provavelmente faz um tail-call, que quebra o hook de
retorno do Frida) — e a conexão acabava caindo depois de algumas chamadas. Fix: usar
`Interceptor.replace` com `NativeFunction` + `NativeCallback`, chamando a função original
manualmente e inspecionando o retorno you mesmo, em vez de depender do `onLeave`.

**Armadilha 2:** API do Frida mudou entre versões — `Module.findExportByName` (função global)
foi substituída por `Process.findModuleByName(x).findExportByName(...)` (método de instância).
`Memory.readByteArray(ptr, len)` virou `ptr.readByteArray(len)` (método do próprio ponteiro).

Com isso, decifrar o **conteúdo real** das chamadas HTTP (`POST /pcs/v1/...`, headers
completos, corpo em JSON, geralmente comprimido em gzip dentro de chunked transfer-encoding)
ficou trivial — é só remontar os chunks de 16KB do `SSL_read`, decodificar o base64, tirar o
chunked encoding manualmente e descomprimir o gzip.

### Passo 3 — achando o endpoint certo

O app usa dois canais separados:
1. **REST `/pcs/v1/...` sobre HTTPS normal** — login, listagem de dispositivos, config.
2. **Canal binário leve** (porta 8883, host `iotmqtt-app-vg-ali.easy4ipcloud.com`) — comandos
   tipo `iot_request`/`iot_response` para leitura de propriedade em tempo real. **Não é MQTT
   nem LeanCloud de verdade** (apesar de parecer, por causa do header `X-LC-TransID` — isso é
   coincidência de nome interno, não a empresa LeanCloud) — é um framing próprio da Dahua,
   complexo demais pra valer a pena replicar.

A saída prática: existe uma chamada REST simples, `POST /pcs/v1/device.info.BasicInfoGet`, com
corpo `{"data":{"productId":"...","deviceId":"..."}}`, que devolve o estado **completo** do
dispositivo, incluindo `properties` com os valores atuais do sensor — sem precisar do canal
binário em tempo real. Suficiente pra polling periódico (um sensor de temperatura não precisa
de push instantâneo).

### Passo 4 — descobrindo o algoritmo de assinatura (`x-pcs-signature`)

Essa foi a parte mais longa. O app tem **múltiplos bundles JavaScript** (React Native) —
alguns embutidos no APK, outros **baixados dinamicamente em runtime** (visto no payload de
`common.service.GetRnInfoByModuleType`: `bundleUrl` apontando pra um `.zip` hospedado em
`file-proxy.imoulife.com`). Patchar o bundle errado (o que vem no APK) não tem efeito nenhum —
é um módulo não relacionado ("addservice-recommend-cn", provavelmente um widget de
recomendação, não o módulo real do sensor).

**Caminho que não funcionou:** o bundle errado tinha um esquema de assinatura baseado em
`MD5(senha_da_conta)` como chave HMAC. Mesmo com a senha real da conta e o algoritmo
aparentemente certo (confirmado contra a string-to-sign exata capturada), a assinatura nunca
bateu — porque esse código nem é o que roda de verdade.

**Caminho que funcionou — interceptar o download do bundle real:**
```bash
# usando o mesmo hook de SSL_read/write, uma captura "cold start" (app do zero)
# flagra a requisicao GET pro .zip do bundle real (ex: "SensorMiddle")
# -> remonta os chunks, salva o .zip, extrai o main.jsbundle de dentro
```
Esse bundle real tinha a função de assinatura correta — mas com uma pegadinha: o header
`x-pcs-signature` usa uma **chave hardcoded fixa no código** (não depende de senha), enquanto
um segundo header (`x-pcs-signature-sha256`, não usado pela maioria dos endpoints) é que
dependia de `SHA256(senha)`. Mesmo essa segunda descoberta estava certa, mas **continuava sem
bater contra chamadas reais capturadas** — sinal de que nem esse bundle específico (de um
módulo de UI chamado "SensorMiddle") é quem assina as chamadas REST principais, só as
chamadas feitas de dentro daquele widget específico.

**O que resolveu de vez — hookear a API Java de criptografia diretamente:**
Em vez de continuar caçando qual dos N bundles JS assina qual chamada, a saída definitiva foi
hookear a camada mais baixa e **garantidamente** usada por qualquer caminho (JS, Java, ou
nativo) que acabe computando um HMAC-SHA256 em Android: a API padrão `javax.crypto`.

```js
Java.perform(function () {
    var SecretKeySpec = Java.use("javax.crypto.spec.SecretKeySpec");
    SecretKeySpec.$init.overload("[B", "java.lang.String").implementation = function (keyBytes, algo) {
        console.log("[SecretKeySpec] algo=" + algo + " keyUtf8=" + /* bytes -> string */);
        return this.$init(keyBytes, algo);
    };

    var Mac = Java.use("javax.crypto.Mac");
    Mac.doFinal.overload("[B").implementation = function (input) {
        var result = this.doFinal(input);
        console.log("[Mac.doFinal] input=" + /* bytes -> string */ + " output=" + /* base64 */);
        return result;
    };
});
```

Isso imediatamente revelou, pra cada chamada real feita pelo app (incluindo
`device.list.DeviceBasicInfoQuery`, `common.service.GetRnInfoByModuleType`, etc): a string
exata que entra no HMAC, e a chave exata usada —
`8b1e940ed6cf7c3fbdb4e5f42335c2ac`, uma string fixa, **igual em todas as chamadas**, sem
nenhuma relação com senha de conta ou sessão. Verificado batendo 100% contra os valores de
`x-pcs-signature` capturados na rede.

**Detalhe que também só apareceu nesse log** (não nos bundles JS examinados antes): a string
assinada usa o **path completo**, incluindo o prefixo `/pcs/v1/` (ex:
`/pcs/v1/device.info.BasicInfoGet`), não só o path relativo — divergência que também explicava
por que tentativas anteriores nunca batiam.

## Lição geral

Quando um app tem múltiplos módulos/bundles de código (nativo + Java + vários bundles JS
estáticos e dinâmicos) e não dá pra saber de antemão qual implementação está realmente ativa
no caminho de execução que importa: **não tente adivinhar lendo código estático.** Hookear a
API mais genérica e de mais baixo nível possível que *qualquer* caminho precisa passar (aqui,
`javax.crypto.Mac`/`SecretKeySpec`) resolve em um passo o que poderia levar horas de leitura de
JS minificado.
