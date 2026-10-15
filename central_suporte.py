# -*- coding: utf-8 -*-
"""
===============================================================================
 CENTRAL DE SUPORTE TECNICO - automacao de rotinas de suporte no Windows
===============================================================================
Interface minimalista (1280x720). Ao clicar em uma acao, o programa abre uma
janela de terminal (cmd) ja executando o comando correspondente.

Requisitos : Windows 10/11 + Python 3.9+ (somente biblioteca padrao).
Uso        : python central_suporte.py   (pede elevacao de administrador)
Executavel : use o gerar_exe.bat (PyInstaller --onefile --noconsole --uac-admin)

ESTRUTURA DO ARQUIVO (use CTRL+F nos titulos abaixo para navegar)
-------------------------------------------------------------------------------
 1. IMPORTS ............ bibliotecas usadas
 2. CONSTANTES/UTILS ... caminhos, flags do Windows, admin, elevacao e log
 3. CATALOGO DE ACOES .. lista ACTIONS: cada botao do programa e seu comando
      3.1 Disco e sistema     3.5 Reparo e limpeza
      3.2 Saude do disco      3.6 Informacoes
      3.3 Rede                3.7 Configuracoes
      3.4 Windows
 4. EXECUCAO ........... run_action(): gera o .bat/.ps1 e abre o terminal
 5. INTERFACE .......... classe App (Tkinter): menu, cartoes, busca, rolagem
 6. PONTO DE ENTRADA ... main(): checa Windows, DPI, admin e abre a janela

FLUXO GERAL
-------------------------------------------------------------------------------
 clique no cartao -> App.on_click() -> (confirmacao) -> (pergunta IP/host)
 -> run_action() -> grava .bat (e .ps1 se for PowerShell) em %TEMP%
 -> abre "cmd.exe /k arquivo.bat" em um novo console -> usuario ve o resultado
===============================================================================
"""

# ----------------------------------------------------------------------------
# 1. IMPORTS
# ----------------------------------------------------------------------------
import ctypes                   # chamadas a API do Windows (admin, DPI, UAC)
import os                       # os.name e os.startfile (abrir o log)
import re                       # regex para validar IP/hostname digitado
import subprocess               # abrir terminais e programas
import sys                      # sys.executable / sys.argv para re-executar como admin
import tempfile                 # pasta %TEMP% do usuario
import textwrap                 # dedent: remove a indentacao dos comandos
import tkinter as tk            # interface grafica
from datetime import datetime   # horario no log e na barra de status
from pathlib import Path        # manipulacao de caminhos
from tkinter import messagebox, simpledialog  # caixas de dialogo (confirmar/perguntar)

# ----------------------------------------------------------------------------
# 2. CONSTANTES E UTILITARIOS
# ----------------------------------------------------------------------------
# Flags de criacao de processo do Windows (valores numericos oficiais).
# Foram escritos como numeros para o arquivo nao quebrar ao ser lido em Linux.
CREATE_NEW_CONSOLE = 0x00000010   # abre o processo em uma janela de console nova
CREATE_NO_WINDOW = 0x08000000     # executa sem mostrar nenhuma janela

# Arquivo de log: registra cada acao executada (data, hora e nome da acao).
LOG = Path(tempfile.gettempdir()) / "suporte_ti.log"

# Pasta onde ficam os .bat/.ps1 temporarios gerados a cada clique.
SCRIPT_DIR = Path(tempfile.gettempdir()) / "suporte_ti_scripts"

# Validacao do que o usuario digita (IP ou hostname). So permite letras,
# numeros, ponto, dois-pontos (IPv6), hifen e sublinhado. Isso impede que
# alguem digite algo como "8.8.8.8 & del *" e injete comandos no terminal.
HOST_RE = re.compile(r"^[A-Za-z0-9._:\-]{1,253}$")


def is_admin() -> bool:
    """Retorna True se o programa esta rodando com privilegios de administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def elevate_and_exit():
    """
    Reabre o programa como administrador (aparece o aviso do UAC) e encerra
    a instancia atual, que nao tem privilegios.
    """
    exe = sys.executable
    if not getattr(sys, "frozen", False):
        # Rodando como .py: prefere pythonw.exe (nao abre console preto).
        pyw = Path(exe).with_name("pythonw.exe")
        if pyw.exists():
            exe = str(pyw)
        params = " ".join(f'"{a}"' for a in sys.argv)        # inclui o nome do script
    else:
        # Rodando como .exe (PyInstaller): o proprio exe ja e o programa.
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
    # Verbo "runas" = "executar como administrador".
    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    sys.exit(0)


def log(msg: str):
    """Acrescenta uma linha com data/hora ao arquivo de log (falhas sao ignoradas)."""
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%d/%m/%Y %H:%M:%S}] {msg}\n")
    except OSError:
        pass


# ----------------------------------------------------------------------------
# 3. CATALOGO DE ACOES
# ----------------------------------------------------------------------------
# Cada botao do programa e um dicionario criado pela funcao add().
#
#   cat     : categoria (aba da barra lateral)
#   name    : titulo do cartao (tambem e o titulo da janela do terminal)
#   desc    : explicacao curta mostrada no cartao
#   kind    : "cmd"    -> linhas de batch executadas num terminal cmd
#             "ps"     -> script PowerShell (salvo em .ps1) executado num terminal
#             "launch" -> abre um programa do Windows, sem terminal
#   body    : o comando em si
#   confirm : se existir, mostra esta pergunta Sim/Nao antes de executar
#   ask     : lista de (chave, pergunta). A resposta substitui @@chave@@ no body
#   risk    : cor da faixa do cartao. 0 = diagnostico (azul),
#             1 = altera o sistema (ambar), 2 = sensivel (vermelho)
# ----------------------------------------------------------------------------
C_DISCO = "Disco e sistema"
C_SAUDE = "Saúde do disco"
C_REDE = "Rede"
C_WIN = "Windows"
C_REPARO = "Reparo e limpeza"
C_INFO = "Informações"
C_CONFIG = "Configurações"
CATEGORIES = [C_DISCO, C_SAUDE, C_REDE, C_WIN, C_REPARO, C_INFO, C_CONFIG]  # ordem do menu

ACTIONS = []  # lista preenchida pelas chamadas add() logo abaixo


def add(cat, name, desc, kind, body, confirm=None, ask=None, risk=None):
    """Registra uma acao no catalogo."""
    # Se nao foi informado risco: acoes com confirmacao sao "ambar", o resto "azul".
    if risk is None:
        risk = 1 if confirm else 0
    ACTIONS.append(dict(
        id=len(ACTIONS),                              # usado no nome do .bat/.ps1 temporario
        cat=cat, name=name, desc=desc, kind=kind,
        body=textwrap.dedent(body).strip("\n"),       # remove indentacao e linhas vazias nas pontas
        confirm=confirm, ask=ask or [], risk=risk))


# Pergunta padrao reutilizada pelas acoes que precisam de IP/hostname.
HOST_ASK = [("alvo", "Digite o IP ou hostname da máquina:")]

# ============================ 3.1 DISCO E SISTEMA ============================

# CHKDSK /F: corrige erros do sistema de arquivos. Na unidade do Windows (em uso)
# o proprio chkdsk pergunta no terminal se deve agendar para o proximo boot.
add(C_DISCO, "Verificar disco (CHKDSK)",
    "Executa chkdsk C: /F. Se a unidade estiver em uso, o terminal pergunta se agenda para o próximo boot.",
    "cmd", "chkdsk C: /F",
    confirm="O CHKDSK pode exigir reinicialização e bloquear a unidade do sistema.\n\nContinuar?")

# SFC: verifica a integridade dos arquivos protegidos do Windows e repara.
add(C_DISCO, "Reparar arquivos do sistema (SFC)",
    "Verifica e repara arquivos protegidos do Windows com sfc /scannow.",
    "cmd", "sfc /scannow")

# DISM: repara a imagem do Windows (a "fonte" que o SFC usa para consertar).
# Ordem: CheckHealth (rapido) -> ScanHealth (varredura) -> RestoreHealth (repara).
add(C_DISCO, "Reparar imagem do Windows (DISM)",
    "Roda CheckHealth, ScanHealth e RestoreHealth em sequência. Pode demorar.",
    "cmd", """
    DISM /Online /Cleanup-Image /CheckHealth
    DISM /Online /Cleanup-Image /ScanHealth
    DISM /Online /Cleanup-Image /RestoreHealth
    """, confirm="O DISM pode levar vários minutos e precisa de internet para baixar componentes.\n\nContinuar?")

# Limpeza de temporarios. "del" apaga arquivos soltos; o "for /d" apaga as
# subpastas. Arquivos em uso sao ignorados (>nul 2>&1 esconde os erros).
# Dentro de um .bat o parametro do for usa %% (dois percentuais).
add(C_DISCO, "Limpar arquivos temporários",
    "Apaga o conteúdo de %TEMP% e de C:\\Windows\\Temp.",
    "cmd", r"""
    rem --- temporarios do usuario ---
    echo Limpando %TEMP% ...
    del /f /s /q "%TEMP%\*.*" >nul 2>&1
    for /d %%D in ("%TEMP%\*") do rd /s /q "%%D" >nul 2>&1
    rem --- temporarios do Windows ---
    echo Limpando %SystemRoot%\Temp ...
    del /f /s /q "%SystemRoot%\Temp\*.*" >nul 2>&1
    for /d %%D in ("%SystemRoot%\Temp\*") do rd /s /q "%%D" >nul 2>&1
    echo Arquivos em uso foram ignorados.
    """, confirm="Apagar os arquivos temporários do usuário e do Windows?")

# defrag /C /O: "/C" todas as unidades, "/O" usa a otimizacao certa para cada
# tipo (desfragmenta HDD, faz TRIM em SSD). "/U" mostra progresso, "/V" detalhes.
add(C_DISCO, "Otimizar / desfragmentar disco",
    "defrag /C /O: desfragmenta HDD e faz TRIM em SSD automaticamente.",
    "cmd", "defrag /C /O /U /V")

# mdsched abre a ferramenta grafica do Windows; o teste so roda ao reiniciar.
add(C_DISCO, "Diagnóstico de memória RAM",
    "Abre o Diagnóstico de Memória do Windows. O teste roda na reinicialização.",
    "launch", "mdsched.exe",
    confirm="O diagnóstico de memória exige reiniciar o computador.\n\nAbrir a ferramenta?")

# WinSAT mede velocidade de leitura/escrita do disco.
add(C_DISCO, "Teste de velocidade do disco (WinSAT)",
    "Mede leitura e escrita sequencial/aleatória com winsat disk.",
    "cmd", "winsat disk")

# ============================ 3.2 SAUDE DO DISCO =============================

# Relatorio completo de saude. Usa Get-PhysicalDisk (status e tipo) e
# Get-StorageReliabilityCounter (contadores SMART: temperatura, desgaste etc).
# Para cada disco monta uma lista de "alertas"; sem alertas = OK.
add(C_SAUDE, "Relatório de saúde (HDD e SSD)",
    "Status, tipo, temperatura, desgaste, horas ligado e erros de cada disco, com veredito OK/Atenção.",
    "ps", r'''
    # Nao interrompe o script se um contador nao existir no disco
    $ErrorActionPreference = 'SilentlyContinue'

    # Funcao auxiliar: mostra "n/d" (nao disponivel) quando o valor e nulo
    function Fmt($v, $suf) { if ($null -eq $v) { 'n/d' } else { "$v$suf" } }

    Write-Host '=== SAUDE DOS DISCOS FISICOS ===' -ForegroundColor Cyan
    $discos = Get-PhysicalDisk
    if (-not $discos) { Write-Host 'Nenhum disco encontrado.' -ForegroundColor Red }
    $problema = $false   # vira $true se algum disco tiver alerta

    foreach ($d in $discos) {
        # Contadores de confiabilidade (SMART) deste disco
        $r = $d | Get-StorageReliabilityCounter

        # ---- Regras de alerta ----
        $alertas = @()
        if ($d.HealthStatus -ne 'Healthy') { $alertas += "Status de saude: $($d.HealthStatus)" }
        if ($d.OperationalStatus -notcontains 'OK') { $alertas += "Status operacional: $($d.OperationalStatus -join ', ')" }
        if ($null -ne $r.Wear -and $r.Wear -ge 80) { $alertas += "Desgaste alto: $($r.Wear)%" }              # SSD muito gasto
        if ($null -ne $r.Temperature -and $r.Temperature -ge 60) { $alertas += "Temperatura alta: $($r.Temperature) C" }
        if ($r.ReadErrorsUncorrected -gt 0) { $alertas += "Erros de leitura nao corrigidos: $($r.ReadErrorsUncorrected)" }
        if ($r.WriteErrorsUncorrected -gt 0) { $alertas += "Erros de escrita nao corrigidos: $($r.WriteErrorsUncorrected)" }

        # ---- Exibicao dos dados ----
        Write-Host ''
        Write-Host ("Disco {0}: {1}" -f $d.DeviceId, $d.FriendlyName) -ForegroundColor Yellow
        Write-Host ("  Tipo ............ {0} ({1})" -f $d.MediaType, $d.BusType)       # HDD/SSD e interface (SATA/NVMe)
        Write-Host ("  Tamanho ......... {0} GB" -f [math]::Round($d.Size / 1GB, 1))
        Write-Host ("  Saude ........... {0} / {1}" -f $d.HealthStatus, ($d.OperationalStatus -join ', '))
        Write-Host ("  Temperatura ..... {0}" -f (Fmt $r.Temperature ' C'))
        Write-Host ("  Desgaste (SSD) .. {0}" -f (Fmt $r.Wear '%'))
        Write-Host ("  Horas ligado .... {0}" -f (Fmt $r.PowerOnHours ' h'))
        Write-Host ("  Erros leitura ... {0}" -f (Fmt $r.ReadErrorsTotal ''))
        Write-Host ("  Erros escrita ... {0}" -f (Fmt $r.WriteErrorsTotal ''))

        # ---- Veredito ----
        if ($alertas.Count -eq 0) {
            Write-Host '  RESULTADO: OK' -ForegroundColor Green
        } else {
            $problema = $true
            Write-Host '  RESULTADO: ATENCAO' -ForegroundColor Red
            $alertas | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
        }
    }

    # ---- Conclusao geral ----
    Write-Host ''
    if ($problema) {
        Write-Host 'Recomendacao: faca backup dos dados importantes e avalie trocar o disco.' -ForegroundColor Red
    } else {
        Write-Host 'Nenhum problema detectado pelos contadores do Windows.' -ForegroundColor Green
    }
    Write-Host 'Obs.: "n/d" significa que o disco/driver nao expoe aquele dado.' -ForegroundColor DarkGray
    ''')

# SMART "PredictFailure": alerta do firmware dizendo que o disco vai falhar em breve.
add(C_SAUDE, "Previsão de falha (SMART)",
    "Consulta o alerta SMART de falha iminente informado pelo firmware do disco.",
    "ps", r'''
    $ErrorActionPreference = 'SilentlyContinue'
    # Classe WMI que expoe o status de previsao de falha de cada disco
    $p = Get-CimInstance -Namespace root\wmi -ClassName MSStorageDriver_FailurePredictStatus
    if (-not $p) {
        # Nem todo disco/controladora expoe esse dado ao Windows
        Write-Host 'Indisponivel: alguns NVMe, USB e controladoras RAID nao expoem o SMART ao Windows.' -ForegroundColor Yellow
    } else {
        $i = 0
        foreach ($x in $p) {
            $i++
            if ($x.PredictFailure) {
                Write-Host "Disco $i : FALHA PREVISTA - faca backup imediatamente!" -ForegroundColor Red
            } else {
                Write-Host "Disco $i : sem falha prevista." -ForegroundColor Green
            }
        }
    }
    ''')

# Mostra se cada disco e HDD ou SSD e se o TRIM (otimizacao de SSD) esta ligado.
add(C_SAUDE, "Identificar HDD ou SSD e TRIM",
    "Mostra o tipo de cada disco e se o TRIM está ativo no Windows.",
    "ps", r'''
    # Tabela com tipo (HDD/SSD), interface e tamanho
    Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, BusType,
        @{n='Tamanho(GB)'; e={[math]::Round($_.Size / 1GB, 1)}} | Format-Table -AutoSize
    # fsutil: DisableDeleteNotify = 0 significa TRIM ativo
    Write-Host 'Status do TRIM (0 = ativo, 1 = desativado):' -ForegroundColor Cyan
    fsutil behavior query DisableDeleteNotify
    ''')

# Espaco total/livre de cada partição (somente volumes que tem letra de unidade).
add(C_SAUDE, "Espaço por partição",
    "Tamanho, espaço livre e saúde de cada volume.",
    "ps", r'''
    Get-Volume | Where-Object { $_.DriveLetter } | Select-Object DriveLetter, FileSystemLabel, FileSystem, HealthStatus,
        @{n='Tamanho(GB)'; e={[math]::Round($_.Size / 1GB, 1)}},
        @{n='Livre(GB)'; e={[math]::Round($_.SizeRemaining / 1GB, 1)}},
        @{n='Livre(%)'; e={ if ($_.Size) { [math]::Round(100 * $_.SizeRemaining / $_.Size, 0) } }} |
        Format-Table -AutoSize
    ''')

# chkdsk /scan: verificacao ONLINE (nao bloqueia a unidade e nao corrige nada).
add(C_SAUDE, "Verificação online (somente leitura)",
    "chkdsk C: /scan: procura erros no sistema de arquivos sem bloquear a unidade.",
    "cmd", "chkdsk C: /scan")

# Le o Log de Eventos "Sistema" procurando erros (Level 1=critico, 2=erro,
# 3=aviso) gerados pelos drivers de disco nos ultimos 30 dias.
add(C_SAUDE, "Erros de disco nos eventos",
    "Lista erros e avisos de disco/NTFS/NVMe/SATA dos últimos 30 dias.",
    "ps", r'''
    $ev = Get-WinEvent -FilterHashtable @{
        LogName = 'System'; ProviderName = 'disk', 'Ntfs', 'stornvme', 'storahci', 'volmgr'
        Level = 1, 2, 3; StartTime = (Get-Date).AddDays(-30) } -MaxEvents 40 -ErrorAction SilentlyContinue
    if (-not $ev) {
        Write-Host 'Nenhum erro de disco registrado nos ultimos 30 dias.' -ForegroundColor Green
    } else {
        # Mostra so a primeira linha da mensagem de cada evento
        $ev | Select-Object TimeCreated, ProviderName, Id,
            @{n='Mensagem'; e={ ($_.Message -split "`n")[0] }} | Format-Table -Wrap -AutoSize
        Write-Host 'Muitos eventos repetidos (ids 7, 11, 51, 55, 153) podem indicar disco ou cabo com problema.' -ForegroundColor Yellow
    }
    ''')

# ReTrim: reenvia o comando TRIM ao SSD para recuperar desempenho.
add(C_SAUDE, "Retrim em SSD",
    "Reenvia o TRIM aos volumes para recuperar desempenho do SSD.",
    "ps", r'''
    # Percorre os volumes fixos com letra e aplica o retrim (HDDs sao ignorados)
    Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' } | ForEach-Object {
        Write-Host "Retrim em $($_.DriveLetter): ..." -ForegroundColor Cyan
        Optimize-Volume -DriveLetter $_.DriveLetter -ReTrim -Verbose -ErrorAction SilentlyContinue
    }
    ''', confirm="O retrim só se aplica a SSDs. Volumes em HDD serão ignorados.\n\nContinuar?")

# ================================ 3.3 REDE ===================================

# Teste basico: ping em dois DNS publicos (Cloudflare e Google) + consulta DNS.
# Se o ping por IP funciona mas o nslookup falha, o problema e o DNS.
add(C_REDE, "Teste de rede (ping e DNS)",
    "Ping em 1.1.1.1 e 8.8.8.8 e consulta DNS de www.microsoft.com.",
    "cmd", """
    ping 1.1.1.1 -n 4
    ping 8.8.8.8 -n 4
    nslookup www.microsoft.com
    """)

# @@alvo@@ e trocado pelo IP/host digitado (ja validado por HOST_RE).
add(C_REDE, "Testar comunicação com uma máquina",
    "Ping e resolução de nome para um IP ou hostname que você informar.",
    "cmd", """
    ping @@alvo@@ -n 4
    echo.
    nslookup @@alvo@@
    """, ask=HOST_ASK)

# tracert: lista cada roteador no caminho ate o destino.
add(C_REDE, "Rota até o destino (tracert)",
    "Mostra os saltos entre este computador e o IP ou hostname informado.",
    "cmd", "tracert @@alvo@@", ask=HOST_ASK)

# Testa as portas mais usadas (RDP 3389, SMB 445, HTTP 80, HTTPS 443, DNS 53, SSH 22)
# com Test-NetConnection e mostra aberta/fechada e a latencia.
add(C_REDE, "Testar portas comuns",
    "Verifica 3389, 445, 80, 443, 53 e 22 em uma máquina e mostra a latência.",
    "ps", r'''
    $alvo = '@@alvo@@'                       # substituido pelo valor digitado
    $ports = 3389, 445, 80, 443, 53, 22
    Write-Host "Testando $alvo ..." -ForegroundColor Cyan
    $res = foreach ($p in $ports) {
        $t = Test-NetConnection -ComputerName $alvo -Port $p -WarningAction SilentlyContinue
        [pscustomobject]@{ Porta = $p; Aberta = $t.TcpTestSucceeded; 'Latencia(ms)' = $t.PingReplyDetails.RoundtripTime }
    }
    $res | Sort-Object Porta | Format-Table -AutoSize
    ''', ask=HOST_ASK)

# Apaga o cache de resolucao de nomes (resolve sites que "nao abrem" apos troca de IP).
add(C_REDE, "Limpar cache DNS",
    "ipconfig /flushdns", "cmd", "ipconfig /flushdns")

# Alem de limpar, pede ao Windows para registrar o nome da maquina no DNS de novo.
add(C_REDE, "Limpar e registrar DNS novamente",
    "Faz flushdns seguido de registerdns.",
    "cmd", """
    ipconfig /flushdns
    ipconfig /registerdns
    """)

# Restaura o Winsock (catalogo de sockets) e a pilha TCP/IP ao padrao.
# Corrige problemas de rede persistentes. Exige reiniciar.
add(C_REDE, "Resetar pilha de rede (Winsock/IP)",
    "netsh winsock reset e netsh int ip reset. Exige reiniciar o PC.",
    "cmd", """
    netsh winsock reset
    netsh int ip reset
    echo.
    echo Reinicie o computador para concluir.
    """, confirm="Isso redefine o Winsock e a pilha TCP/IP. Será necessário reiniciar.\n\nContinuar?")

# ipconfig /all: IP, mascara, gateway, DNS, MAC e se o DHCP esta ativo.
add(C_REDE, "IPConfig detalhado",
    "ipconfig /all com IP, máscara, gateway, DNS e MAC.",
    "cmd", "ipconfig /all")

# Libera o IP atual, pede outro ao DHCP e limpa a tabela ARP (IP -> MAC).
add(C_REDE, "Renovar IP e limpar cache ARP",
    "Faz release, renew e apaga a tabela ARP. A conexão cai por alguns segundos.",
    "cmd", """
    ipconfig /release
    ipconfig /renew
    arp -d *
    """, confirm="A conexão de rede será interrompida por alguns segundos.\n\nContinuar?")

# netstat -ano: conexoes ativas, portas abertas e o PID do processo dono.
add(C_REDE, "Conexões ativas (netstat)",
    "netstat -ano: portas abertas e PID de cada conexão.",
    "cmd", """
    netstat -ano
    echo.
    echo Dica: associe o PID ao processo no Gerenciador de Tarefas.
    """)

# =============================== 3.4 WINDOWS =================================

# Acoes "launch": abrem programas do Windows direto (sem terminal).
add(C_WIN, "Gerenciador de Tarefas", "Abre o Gerenciador de Tarefas.", "launch", "start \"\" taskmgr")
add(C_WIN, "Visualizar logs de eventos", "Abre o Visualizador de Eventos.", "launch", "start \"\" eventvwr.msc")

# A variavel devmgr_show_nonpresent_devices=1 faz o Gerenciador de Dispositivos
# listar drivers de aparelhos que nao estao mais conectados.
add(C_WIN, "Gerenciador de dispositivos (ocultos)",
    "Abre o gerenciador já preparado para mostrar drivers ocultos.",
    "cmd", """
    set devmgr_show_nonpresent_devices=1
    start "" devmgmt.msc
    echo No menu Exibir, marque "Mostrar dispositivos ocultos".
    """)

# usoclient StartScan pede ao Windows para procurar atualizacoes agora.
add(C_WIN, "Windows Update (buscar/abrir)",
    "Dispara a busca por atualizações e abre a tela do Windows Update.",
    "cmd", """
    usoclient.exe StartScan
    start "" ms-settings:windowsupdate
    echo Busca iniciada.
    """)

# Reset do Windows Update: para os servicos, renomeia as pastas de cache
# (o Windows recria limpas), reinicia os servicos e dispara nova busca.
add(C_WIN, "Resetar Windows Update",
    "Para os serviços, renomeia SoftwareDistribution e Catroot2 e reinicia tudo.",
    "cmd", r"""
    rem --- 1) parar os servicos (Update, BITS, Criptografia, Instalador) ---
    echo Parando servicos...
    net stop wuauserv
    net stop bits
    net stop cryptsvc
    net stop msiserver
    rem --- 2) renomear as pastas de cache (apaga a copia .old antiga antes) ---
    echo Renomeando pastas de cache...
    if exist "%SystemRoot%\SoftwareDistribution.old" rd /s /q "%SystemRoot%\SoftwareDistribution.old"
    if exist "%SystemRoot%\System32\Catroot2.old" rd /s /q "%SystemRoot%\System32\Catroot2.old"
    if exist "%SystemRoot%\SoftwareDistribution" ren "%SystemRoot%\SoftwareDistribution" SoftwareDistribution.old
    if exist "%SystemRoot%\System32\Catroot2" ren "%SystemRoot%\System32\Catroot2" Catroot2.old
    rem --- 3) limpar fila de downloads travada do BITS ---
    del /f /q "%ALLUSERSPROFILE%\Application Data\Microsoft\Network\Downloader\qmgr*.dat" >nul 2>&1
    rem --- 4) iniciar os servicos novamente e buscar atualizacoes ---
    echo Iniciando servicos...
    net start msiserver
    net start cryptsvc
    net start bits
    net start wuauserv
    usoclient.exe StartScan
    echo Tente verificar as atualizacoes novamente.
    """, confirm="Isso reinicia os componentes do Windows Update.\n\nContinuar?")

# Tres acoes de firewall: mostrar, ativar, desativar (netsh advfirewall).
add(C_WIN, "Firewall: mostrar status", "Exibe o estado do firewall em todos os perfis.",
    "cmd", "netsh advfirewall show allprofiles state")
add(C_WIN, "Firewall: ativar", "Ativa o firewall em todos os perfis.",
    "cmd", """
    netsh advfirewall set allprofiles state on
    netsh advfirewall show allprofiles state
    """, confirm="Ativar o Firewall do Windows em todos os perfis?")
add(C_WIN, "Firewall: desativar", "Desliga o firewall em todos os perfis. Use só para teste.",
    "cmd", """
    netsh advfirewall set allprofiles state off
    netsh advfirewall show allprofiles state
    echo.
    echo ATENCAO: reative o firewall ao terminar o teste.
    """, confirm="Tem certeza que deseja DESATIVAR o firewall em todas as redes?", risk=2)

# Limpa trabalhos de impressao travados: para o spooler, apaga os arquivos da
# fila (pasta PRINTERS) e liga o spooler novamente.
add(C_WIN, "Limpar fila de impressão",
    "Para o spooler, apaga os trabalhos travados e reinicia o serviço.",
    "cmd", r"""
    net stop spooler
    del /f /q "%SystemRoot%\System32\spool\PRINTERS\*.*"
    net start spooler
    echo Fila de impressao limpa.
    """, confirm="Todos os trabalhos pendentes na fila local serão apagados.\n\nContinuar?")

# ========================= 3.5 REPARO E LIMPEZA (EXTRA) ======================

# Reset do driver de video: desativa e reativa o adaptador grafico no
# Gerenciador de Dispositivos (equivale a reinstalar a "ligacao" do driver).
add(C_REPARO, "Reiniciar driver de vídeo",
    "Desativa e reativa o adaptador de vídeo. A tela pisca ou fica preta por alguns segundos.",
    "ps", r'''
    # Pega todos os adaptadores de video ativos (Status OK)
    Get-PnpDevice -Class Display -Status OK -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "Reiniciando: $($_.FriendlyName)" -ForegroundColor Cyan
        Disable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false   # desliga
        Start-Sleep -Seconds 3                                         # espera
        Enable-PnpDevice -InstanceId $_.InstanceId -Confirm:$false    # liga de novo
    }
    Write-Host 'Concluido.' -ForegroundColor Green
    ''', confirm="A tela vai piscar ou ficar preta por alguns segundos. Salve seu trabalho antes.\n\nContinuar?")

# Cache de shaders (DirectX/NVIDIA/AMD): arquivos temporarios da placa de video.
# Se corrompem, causam travadas e falhas graficas; o Windows recria sozinho.
add(C_REPARO, "Limpar cache de shaders da GPU",
    "Apaga caches do DirectX, NVIDIA e AMD. Ajuda com travamentos e artefatos em jogos.",
    "ps", r'''
    $alvos = @(
        "$env:LOCALAPPDATA\D3DSCache", "$env:LOCALAPPDATA\NVIDIA\DXCache", "$env:LOCALAPPDATA\NVIDIA\GLCache",
        "$env:LOCALAPPDATA\AMD\DxCache", "$env:LOCALAPPDATA\AMD\GLCache")
    foreach ($a in $alvos) {
        if (Test-Path $a) {                                            # so limpa o que existe
            Remove-Item "$a\*" -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "Limpo: $a" -ForegroundColor Green
        }
    }
    Write-Host 'Os caches serao recriados no proximo uso.'
    ''', confirm="Fechar jogos e apps gráficos antes de continuar.\n\nLimpar o cache de shaders?")

# Cache de icones/miniaturas: apagar corrige icones em branco ou errados.
# O Explorer precisa ser fechado antes, pois mantem esses arquivos abertos.
add(C_REPARO, "Limpar cache de ícones e miniaturas",
    "Corrige ícones em branco e miniaturas erradas. O Explorer reinicia.",
    "cmd", r"""
    rem --- fecha o Explorer (libera os arquivos de cache) ---
    taskkill /f /im explorer.exe
    rem --- apaga os bancos de icones e miniaturas ---
    del /f /q "%LOCALAPPDATA%\IconCache.db" >nul 2>&1
    del /f /a /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db" >nul 2>&1
    del /f /a /q "%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db" >nul 2>&1
    rem --- reabre o Explorer (reconstroi o cache) ---
    start explorer.exe
    echo Cache reconstruido.
    """, confirm="A barra de tarefas e as pastas vão fechar e reabrir.\n\nContinuar?")

# Reinicia so o Explorer (barra de tarefas/area de trabalho) sem deslogar.
add(C_REPARO, "Reiniciar o Explorer",
    "Reinicia a área de trabalho e a barra de tarefas sem deslogar.",
    "cmd", """
    taskkill /f /im explorer.exe
    start explorer.exe
    """)

# wsreset limpa o cache da Microsoft Store (abre a loja ao terminar).
add(C_REPARO, "Resetar cache da Microsoft Store",
    "Executa wsreset para consertar downloads e abertura da loja.",
    "cmd", "wsreset.exe")

# Registra de novo todos os apps (AppX) usando o manifesto de cada um.
# Resolve menu Iniciar/Configuracoes/Store que nao abrem. Erros isolados sao normais.
add(C_REPARO, "Re-registrar apps do Windows",
    "Registra novamente os apps da Store e do sistema (menu Iniciar, Configurações). Demora.",
    "ps", r'''
    Get-AppxPackage -AllUsers | ForEach-Object {
        $m = Join-Path $_.InstallLocation 'AppXManifest.xml'          # manifesto do app
        if (Test-Path $m) { Add-AppxPackage -DisableDevelopmentMode -Register $m -ErrorAction SilentlyContinue }
    }
    Write-Host 'Concluido. Erros isolados sao normais.' -ForegroundColor Green
    ''', confirm="O processo pode levar vários minutos e exibir avisos.\n\nContinuar?")

# Reinicia o servico de audio. O AudioEndpointBuilder e dependencia do audiosrv,
# por isso para na ordem audiosrv -> builder e inicia na ordem inversa.
add(C_REPARO, "Reiniciar serviço de áudio",
    "Reinicia Windows Audio e o Audio Endpoint Builder quando o som some.",
    "cmd", """
    net stop audiosrv
    net stop AudioEndpointBuilder
    net start AudioEndpointBuilder
    net start audiosrv
    """)

# Apaga somente pastas de cache (Cache e Code Cache) de TODOS os perfis do
# Edge e do Chrome. Senhas, favoritos e historico nao sao tocados.
add(C_REPARO, "Limpar cache de Edge e Chrome",
    "Apaga o cache de todos os perfis. Não remove senhas nem favoritos.",
    "ps", r'''
    $pastas = @(
        "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Cache\*",
        "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Code Cache\*",
        "$env:LOCALAPPDATA\Google\Chrome\User Data\*\Cache\*",
        "$env:LOCALAPPDATA\Google\Chrome\User Data\*\Code Cache\*")
    foreach ($p in $pastas) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Host 'Cache dos navegadores limpo.' -ForegroundColor Green
    ''', confirm="Feche o Edge e o Chrome antes de continuar.\n\nLimpar o cache?")

# Esvazia a lixeira de todas as unidades (exclusao permanente).
add(C_REPARO, "Esvaziar lixeira",
    "Remove definitivamente os itens da lixeira de todas as unidades.",
    "ps", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue; Write-Host 'Lixeira esvaziada.' -ForegroundColor Green",
    confirm="Os arquivos da lixeira serão apagados de forma permanente.\n\nContinuar?")

# ============================== 3.6 INFORMACOES ==============================

# Inventario da maquina (ideia da imagem 4): coleta os dados, mostra no terminal
# e grava um .txt na area de trabalho com nome da maquina + data/hora.
add(C_INFO, "Inventário da máquina (.txt)",
    "Hostname, usuário, rede, discos, CPU, RAM e Windows. Salva um .txt na área de trabalho.",
    "ps", r'''
    $ErrorActionPreference = 'SilentlyContinue'

    # Converte o tamanho do prefixo (ex.: 24) em mascara (255.255.255.0)
    function Mask($len) {
        $bin = ('1' * $len).PadRight(32, '0')                                    # 24 uns + zeros = 32 bits
        (0..3 | ForEach-Object { [Convert]::ToInt32($bin.Substring($_ * 8, 8), 2) }) -join '.'   # 4 blocos de 8 bits
    }

    # ---- Caminho do arquivo de saida (area de trabalho, mesmo com OneDrive) ----
    $desk = [Environment]::GetFolderPath('Desktop')
    $stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm'
    $file = Join-Path $desk "Inventario_$($env:COMPUTERNAME)_$stamp.txt"

    # ---- Coleta de dados (WMI/CIM) ----
    $os = Get-CimInstance Win32_OperatingSystem      # Windows
    $cs = Get-CimInstance Win32_ComputerSystem       # fabricante, modelo, RAM
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $bios = Get-CimInstance Win32_BIOS               # numero de serie

    # ---- Monta o relatorio: tudo que o bloco emite vira uma linha de texto ----
    $report = & {
        '=============================================='
        " INVENTARIO - $($env:COMPUTERNAME)"
        " Gerado em: $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')"
        '=============================================='
        ''
        '[IDENTIFICACAO]'
        "Hostname .......: $($env:COMPUTERNAME)"
        "Usuario logado .: $($env:USERDOMAIN)\$($env:USERNAME)"
        "Fabricante/Modelo: $($cs.Manufacturer) $($cs.Model)"
        "Numero de serie : $($bios.SerialNumber)"
        ''
        '[REDE]'
        # Uma entrada por adaptador que tenha IPv4
        foreach ($c in (Get-NetIPConfiguration | Where-Object { $_.IPv4Address })) {
            $mac = (Get-NetAdapter -Name $c.InterfaceAlias).MacAddress
            "Interface ......: $($c.InterfaceAlias)"
            "IP .............: $($c.IPv4Address.IPAddress)"
            "Mascara ........: $(Mask $c.IPv4Address.PrefixLength)"
            "Gateway ........: $($c.IPv4DefaultGateway.NextHop)"
            "MAC ............: $mac"
            "DNS ............: $(($c.DNSServer.ServerAddresses) -join ', ')"
            ''
        }
        '[DISCOS - ESPACO POR PARTICAO]'
        Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {     # DriveType=3: discos locais
            "{0} Total: {1} GB | Livre: {2} GB ({3}%)" -f $_.DeviceID, [math]::Round($_.Size / 1GB, 1),
                [math]::Round($_.FreeSpace / 1GB, 1), [math]::Round(100 * $_.FreeSpace / $_.Size, 0)
        }
        ''
        '[PROCESSADOR E MEMORIA]'
        "Processador ....: $($cpu.Name.Trim())"
        "Nucleos/Threads : $($cpu.NumberOfCores) / $($cpu.NumberOfLogicalProcessors)"
        "Memoria RAM ....: $([math]::Round($cs.TotalPhysicalMemory / 1GB, 1)) GB"
        ''
        '[WINDOWS]'
        "Sistema ........: $($os.Caption)"
        "Versao/Build ...: $($os.Version) (build $($os.BuildNumber))"
        "Arquitetura ....: $($os.OSArchitecture)"
        "Fabricante .....: $($os.Manufacturer)"
        "Instalado em ...: $($os.InstallDate)"
    }

    # ---- Saidas: arquivo .txt, tela do terminal e Bloco de Notas ----
    $report | Out-File -FilePath $file -Encoding UTF8
    $report | ForEach-Object { Write-Host $_ }
    Write-Host ''
    Write-Host "Arquivo salvo em: $file" -ForegroundColor Green
    Start-Process notepad.exe $file
    ''')

# systeminfo: resumo completo do Windows, hotfixes, memoria, rede etc.
add(C_INFO, "Informações do sistema", "Executa systeminfo.", "cmd", "systeminfo")

# Hardware detalhado por CIM (substitui o antigo WMIC, removido do Windows 11 novo).
add(C_INFO, "Informações de hardware",
    "Placa-mãe, BIOS, CPU, memórias, placa de vídeo e discos.",
    "ps", r'''
    # Funcao auxiliar para imprimir o titulo de cada bloco
    function T($t) { Write-Host ''; Write-Host "--- $t ---" -ForegroundColor Cyan }
    T 'Placa-mae';  Get-CimInstance Win32_BaseBoard | Format-List Manufacturer, Product, SerialNumber
    T 'BIOS';       Get-CimInstance Win32_BIOS | Format-List Manufacturer, SMBIOSBIOSVersion, ReleaseDate
    T 'Processador'; Get-CimInstance Win32_Processor | Format-List Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed
    T 'Memorias';   Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel, Manufacturer, PartNumber, Speed,
                        @{n='GB'; e={$_.Capacity / 1GB}} | Format-Table -AutoSize
    T 'Video';      Get-CimInstance Win32_VideoController | Format-List Name, DriverVersion, @{n='VRAM(GB)'; e={[math]::Round($_.AdapterRAM / 1GB, 1)}}
    T 'Discos';     Get-CimInstance Win32_DiskDrive | Format-List Model, InterfaceType, SerialNumber, @{n='GB'; e={[math]::Round($_.Size / 1GB, 1)}}
    ''')

# Le a chave OEM gravada na BIOS e mostra o estado da licenca (slmgr /xpr).
# Marcada como "sensivel" (risk=2) porque expoe um dado de licenciamento.
add(C_INFO, "Chave de produto do Windows",
    "Mostra a chave gravada na BIOS (OEM) e o estado da licença.",
    "ps", r'''
    $k = (Get-CimInstance SoftwareLicensingService).OA3xOriginalProductKey
    if ($k) { Write-Host "Chave na BIOS: $k" -ForegroundColor Green }
    else { Write-Host 'Nenhuma chave OEM na BIOS (licenca digital ou volume).' -ForegroundColor Yellow }
    Write-Host ''
    cscript //nologo "$env:windir\system32\slmgr.vbs" /xpr     # estado da ativacao
    ''', risk=2)

# Bateria: carga atual + relatorio HTML do Windows (capacidade de projeto x atual).
add(C_INFO, "Status da bateria (notebook)",
    "Carga atual e relatório HTML de saúde da bateria, salvo na área de trabalho.",
    "ps", r'''
    Get-CimInstance Win32_Battery | Format-List Name, EstimatedChargeRemaining, BatteryStatus, EstimatedRunTime
    $f = Join-Path ([Environment]::GetFolderPath('Desktop')) 'relatorio_bateria.html'
    powercfg /batteryreport /output $f          # gera o relatorio
    if (Test-Path $f) { Start-Process $f }      # abre no navegador
    ''')

# ============================= 3.7 CONFIGURACOES =============================

# Ponto de restauracao: "foto" do sistema para desfazer mudancas se algo der errado.
add(C_CONFIG, "Criar ponto de restauração",
    "Cria um ponto de restauração do sistema antes de mudanças grandes.",
    "ps", r'''
    Enable-ComputerRestore -Drive "$env:SystemDrive\"     # garante que a protecao esta ligada
    Checkpoint-Computer -Description 'Ponto de Restauracao Manual (Suporte)' -RestorePointType MODIFY_SETTINGS
    Write-Host 'Se nada foi criado, o Windows limita a 1 ponto a cada 24 horas.' -ForegroundColor DarkGray
    ''', confirm="Criar um ponto de restauração agora?")

# Sincroniza o relogio (liga o servico de hora, forca a sincronizacao e mostra o status).
add(C_CONFIG, "Sincronizar hora (w32tm)",
    "Ressincroniza o relógio com o servidor de hora.",
    "cmd", """
    net start w32time
    w32tm /resync
    w32tm /query /status
    """)

# pnputil exporta todos os drivers de terceiros para uma pasta datada.
add(C_CONFIG, "Backup de drivers",
    "Exporta todos os drivers de terceiros para C:\\BackupDrivers.",
    "ps", r'''
    $dest = "C:\BackupDrivers\$(Get-Date -Format 'yyyy-MM-dd_HH-mm')"      # pasta com data e hora
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    pnputil /export-driver * $dest
    Write-Host "Drivers exportados para: $dest" -ForegroundColor Green
    ''', confirm="A exportação pode demorar e usar vários GB de espaço.\n\nContinuar?")

# winget atualiza todos os programas instalados; os parametros aceitam os termos automaticamente.
add(C_CONFIG, "Atualizar programas (winget)",
    "winget upgrade --all: atualiza todos os programas compatíveis.",
    "cmd", "winget upgrade --all --accept-source-agreements --accept-package-agreements",
    confirm="Atualizar todos os programas instalados via winget?")

# Reaplica as politicas de grupo (GPO) do dominio sem esperar o ciclo automatico.
add(C_CONFIG, "Forçar políticas de grupo",
    "gpupdate /force: reaplica as políticas do domínio.",
    "cmd", "gpupdate /force")

# Conta de administrador interna: localizada pelo SID terminado em -500, que e
# sempre o mesmo, em qualquer idioma (no Windows em ingles o nome e "Administrator").
add(C_CONFIG, "Ativar conta Administrador local",
    "Ativa a conta interna de administrador (SID -500), em qualquer idioma do Windows.",
    "ps", r'''
    $a = Get-LocalUser | Where-Object { $_.SID.Value -like '*-500' }
    Enable-LocalUser -Name $a.Name
    Write-Host "Conta '$($a.Name)' ativada. Defina uma senha forte antes de usar." -ForegroundColor Yellow
    ''', confirm="Ativar a conta de administrador interna só deve ser feito quando necessário.\n\nContinuar?", risk=2)
add(C_CONFIG, "Desativar conta Administrador local",
    "Desfaz a ativação da conta interna de administrador.",
    "ps", r'''
    $a = Get-LocalUser | Where-Object { $_.SID.Value -like '*-500' }
    Disable-LocalUser -Name $a.Name
    Write-Host "Conta '$($a.Name)' desativada." -ForegroundColor Green
    ''', confirm="Desativar a conta de administrador interna?", risk=1)


# ----------------------------------------------------------------------------
# 4. EXECUCAO
# ----------------------------------------------------------------------------
# Cabecalho e rodape colocados em volta de todo comando "cmd"/"ps".
#   @echo off  -> nao mostra cada linha do .bat
#   chcp 65001 -> codificacao UTF-8 (acentos corretos no terminal)
#   title/color-> titulo da janela e cor (0B = fundo preto, texto azul-claro)
BAT_HEADER = """@echo off
chcp 65001 >nul
title @@TITLE@@
color 0B
echo ======================================================
echo  @@TITLE@@
echo ======================================================
echo.
"""
BAT_FOOTER = """
echo.
echo ------------------------------------------------------
echo  Concluido. Voce pode fechar esta janela.
echo ------------------------------------------------------
"""


def run_action(act, values):
    """
    Executa uma acao do catalogo.
      act    : dicionario criado por add()
      values : respostas do usuario (ex.: {"alvo": "192.168.0.1"})
    """
    # 1) Troca os marcadores @@chave@@ pelos valores digitados (ja validados).
    body = act["body"]
    for k, v in values.items():
        body = body.replace(f"@@{k}@@", v)

    # 2) Registra no log.
    log(f"{act['name']} {values if values else ''}")

    # 3) Acao "launch": apenas abre o programa, sem terminal.
    if act["kind"] == "launch":
        subprocess.Popen(body, shell=True, creationflags=CREATE_NO_WINDOW)
        return

    # 4) Prepara a pasta temporaria dos scripts.
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    # 5) Acao PowerShell: salva o script em .ps1 e o .bat so chama esse arquivo.
    #    Isso evita problemas de aspas e caracteres especiais na linha de comando.
    if act["kind"] == "ps":
        ps1 = SCRIPT_DIR / f"acao_{act['id']}.ps1"
        ps1.write_text(body, encoding="utf-8-sig")   # BOM: o PowerShell 5 le acentos corretamente
        commands = f'powershell -NoProfile -ExecutionPolicy Bypass -File "{ps1}"'
    else:
        commands = body                               # acao "cmd": as linhas vao direto no .bat

    # 6) Monta o .bat final (cabecalho + comandos + rodape).
    bat = SCRIPT_DIR / f"acao_{act['id']}.bat"
    content = BAT_HEADER.replace("@@TITLE@@", act["name"]) + commands + BAT_FOOTER
    bat.write_text(content, encoding="utf-8")

    # 7) Abre o terminal. "/k" executa o .bat e MANTEM a janela aberta,
    #    para o usuario ler o resultado. CREATE_NEW_CONSOLE = janela nova.
    subprocess.Popen(["cmd.exe", "/k", str(bat)], creationflags=CREATE_NEW_CONSOLE)


# ----------------------------------------------------------------------------
# 5. INTERFACE (Tkinter)
# ----------------------------------------------------------------------------
# Paleta de cores. Claro e frio: barra lateral azul-ardosia, area de trabalho
# cinza-azulada e cartoes brancos.
BG = "#EEF1F4"          # fundo da area principal
SIDEBAR = "#1F2A37"     # fundo da barra lateral
SIDE_HOVER = "#2B3A4C"  # item da barra com mouse em cima
SIDE_ACTIVE = "#3A4D66" # item da barra selecionado
SIDE_TEXT = "#E3E9F0"
SIDE_MUTED = "#8FA0B3"
CARD = "#FFFFFF"        # fundo do cartao
CARD_HOVER = "#E8EEFC"  # cartao com mouse em cima
BORDER = "#D5DBE3"
TEXT = "#1B2430"
MUTED = "#5B6675"
RISK_COLORS = {0: "#2F5BEA", 1: "#D18A00", 2: "#C0392B"}   # faixa lateral: azul / ambar / vermelho
FONT = "Segoe UI"       # fonte nativa do Windows


# Tamanho-base do design (em pixels "logicos", a 100% de escala do Windows).
BASE_W, BASE_H = 1280, 720   # janela
SIDE_W = 270                 # largura da barra lateral


class App(tk.Tk):
    COLS = 3  # numero de cartoes por linha

    # ---- 5.1 escala e medidas ----------------------------------------------
    # Problema que isto resolve: em telas com escala maior que 100% (125%, 150%)
    # as fontes crescem mas os tamanhos em pixels nao, e os textos ficavam
    # cortados. Agora TUDO (janela, margens, fontes) usa o mesmo fator self.f.
    def px(self, n):
        """Converte um tamanho em pixels de design para pixels reais da tela."""
        return int(round(n * self.f))

    def font(self, pt, *styles):
        """
        Fonte em PIXELS (tamanho negativo no Tk), ja multiplicada pelo fator
        de escala. Assim o texto cresce junto com o resto do layout.
        styles: "bold", "underline"...
        """
        return (FONT, -max(9, round(pt * 96 / 72 * self.f)), *styles)

    # ---- 5.2 construcao da janela ------------------------------------------
    def __init__(self):
        super().__init__()
        self.title("Central de Suporte Técnico")

        # Fator de escala = escala do Windows, limitado para a janela caber na tela
        # (deixa uma folga para a barra de tarefas e a barra de titulo).
        dpi = self.winfo_fpixels("1i") / 96.0
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.f = max(0.6, min(dpi, (sw - 20) / BASE_W, (sh - 90) / BASE_H))

        # Janela fixa (1280x720 a 100%), centralizada na tela.
        w, h = round(BASE_W * self.f), round(BASE_H * self.f)
        x = max((sw - w) // 2, 0)
        y = max((sh - h) // 2 - 20, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.resizable(False, False)
        self.configure(bg=BG)

        # Estado da interface.
        self.current = CATEGORIES[0]          # categoria selecionada
        self.side_items = {}                  # categoria -> widgets do item na barra lateral
        self.search_var = tk.StringVar()      # texto da caixa de busca
        self.status_var = tk.StringVar(       # texto da barra de status
            value="Escolha uma ação. O terminal abre com o comando já em execução.")

        # Monta as tres areas da janela.
        self._build_sidebar()
        self._build_main()
        self._build_status()

        # Toda vez que o texto da busca mudar, redesenha os cartoes.
        self.search_var.trace_add("write", lambda *_: self.refresh())
        self.refresh()

    def _build_sidebar(self):
        """Barra lateral: titulo, lista de categorias, aviso de admin e link do log."""
        px = self.px
        side = tk.Frame(self, bg=SIDEBAR, width=px(SIDE_W))
        side.pack(side="left", fill="y")
        side.pack_propagate(False)            # mantem a largura fixa
        pad = 22                              # margem lateral dos textos
        text_w = px(SIDE_W - 2 * pad)         # largura util: textos longos quebram linha em vez de cortar

        tk.Label(side, text="Central de suporte", bg=SIDEBAR, fg="#FFFFFF",
                 font=self.font(15, "bold"), anchor="w", justify="left",
                 wraplength=text_w).pack(fill="x", padx=px(pad), pady=(px(28), px(2)))
        tk.Label(side, text="Automação de rotinas do Windows", bg=SIDEBAR, fg=SIDE_MUTED,
                 font=self.font(9), anchor="w", justify="left",
                 wraplength=text_w).pack(fill="x", padx=px(pad), pady=(0, px(24)))

        # Um item clicavel por categoria (nome + quantidade de acoes).
        for cat in CATEGORIES:
            n = sum(1 for a in ACTIONS if a["cat"] == cat)
            row = tk.Frame(side, bg=SIDEBAR, cursor="hand2")
            row.pack(fill="x", padx=px(10), pady=px(1))
            name = tk.Label(row, text=cat, bg=SIDEBAR, fg=SIDE_TEXT, font=self.font(11), anchor="w")
            name.pack(side="left", padx=(px(12), 0), pady=px(9))
            count = tk.Label(row, text=str(n), bg=SIDEBAR, fg=SIDE_MUTED, font=self.font(9))
            count.pack(side="right", padx=px(12))
            parts = [row, name, count]
            self.side_items[cat] = parts
            # Clique seleciona a categoria; entrar/sair do mouse muda a cor.
            for p in parts:
                p.bind("<Button-1>", lambda _e, c=cat: self.select_category(c))
                p.bind("<Enter>", lambda _e, c=cat: self._side_color(c, hover=True))
                p.bind("<Leave>", lambda _e, c=cat: self._side_color(c, hover=False))

        # Espaco flexivel empurra o rodape da barra para baixo.
        tk.Frame(side, bg=SIDEBAR).pack(expand=True, fill="both")

        # Aviso sobre privilegios de administrador (verde = ok, laranja = sem admin).
        admin_ok = is_admin()
        tk.Label(side, text="Executando como administrador" if admin_ok else "Sem privilégios de administrador",
                 bg=SIDEBAR, fg="#7FD39B" if admin_ok else "#F2B86B", font=self.font(9),
                 anchor="w", justify="left", wraplength=text_w).pack(fill="x", padx=px(pad), pady=(0, px(6)))

        # Link que abre o arquivo de log.
        link = tk.Label(side, text="Abrir arquivo de log", bg=SIDEBAR, fg=SIDE_TEXT,
                        font=self.font(9, "underline"), anchor="w", cursor="hand2")
        link.pack(fill="x", padx=px(pad), pady=(0, px(22)))
        link.bind("<Button-1>", lambda _e: self.open_log())

    def _build_main(self):
        """Area principal: titulo + busca no topo e area rolavel de cartoes."""
        px = self.px
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        # ---- topo: titulo da categoria (esquerda) e busca (direita) ----
        top = tk.Frame(main, bg=BG)
        top.pack(fill="x", padx=px(28), pady=(px(24), px(12)))
        self.title_lbl = tk.Label(top, text="", bg=BG, fg=TEXT, font=self.font(18, "bold"), anchor="w")
        self.title_lbl.pack(side="left")

        box = tk.Frame(top, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        box.pack(side="right")
        tk.Label(box, text="Buscar", bg=CARD, fg=MUTED, font=self.font(10)).pack(side="left", padx=(px(10), px(4)))
        self.search = tk.Entry(box, textvariable=self.search_var, relief="flat", bg=CARD, fg=TEXT,
                               insertbackground=TEXT, font=self.font(11), width=22)
        self.search.pack(side="left", padx=(0, px(10)), pady=px(7))

        # ---- area rolavel: Canvas + Frame interno (Tkinter nao tem frame rolavel pronto) ----
        wrap = tk.Frame(main, bg=BG)
        wrap.pack(fill="both", expand=True, padx=(px(28), px(16)), pady=(0, px(40)))  # folga embaixo p/ barra de status
        self.canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        self.inner = tk.Frame(self.canvas, bg=BG)                        # os cartoes ficam aqui dentro
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.pack(fill="both", expand=True)
        # Ajusta a regiao de rolagem quando o conteudo muda de tamanho...
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        # ...e a largura do conteudo quando a janela muda.
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width - px(12)))
        # Roda do mouse rola a lista.
        self.bind_all("<MouseWheel>", self._on_wheel)

    def _build_status(self):
        """Barra inferior: mensagem da ultima acao e legenda das cores."""
        px = self.px
        bar = tk.Frame(self, bg=BG)
        bar.place(relx=0, rely=1.0, anchor="sw", x=px(SIDE_W), relwidth=1.0, width=-px(SIDE_W), height=px(34))
        # Legenda (empacotada da direita para a esquerda) - fica reservada primeiro...
        for risk, text in ((2, "Sensível"), (1, "Altera o sistema"), (0, "Diagnóstico")):
            tk.Label(bar, text=text, bg=BG, fg=MUTED, font=self.font(9)).pack(side="right", padx=(0, px(16)))
            tk.Frame(bar, bg=RISK_COLORS[risk], width=px(10), height=px(10)).pack(side="right", padx=(0, px(5)))
        # ...e a mensagem de status ocupa o espaco que sobrar (corta no fim, sem invadir a legenda).
        tk.Label(bar, textvariable=self.status_var, bg=BG, fg=MUTED, font=self.font(9),
                 anchor="w").pack(side="left", padx=px(28))

    # ---- 5.3 comportamento -------------------------------------------------
    def _on_wheel(self, event):
        """Rola a lista com a roda do mouse, mas so se o conteudo for maior que a area visivel."""
        if self.inner.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-event.delta / 120) * 2, "units")

    def _side_color(self, cat, hover):
        """Pinta o item da barra lateral: selecionado > mouse em cima > normal."""
        active = cat == self.current and not self.search_var.get().strip()
        color = SIDE_ACTIVE if active else (SIDE_HOVER if hover else SIDEBAR)
        for p in self.side_items[cat]:
            p.configure(bg=color)

    def select_category(self, cat):
        """Troca de categoria (limpando a busca, se houver)."""
        self.current = cat
        if self.search_var.get():
            self.search_var.set("")   # isso ja dispara refresh() pelo trace
        else:
            self.refresh()

    def refresh(self):
        """Redesenha a area principal conforme a categoria ou a busca atual."""
        for cat in self.side_items:
            self._side_color(cat, hover=False)
        q = self.search_var.get().strip().lower()
        if q:
            # Busca em todas as categorias: procura no nome, descricao e categoria.
            items = [a for a in ACTIONS if q in f"{a['name']} {a['desc']} {a['cat']}".lower()]
            self.title_lbl.configure(text=f"Resultados ({len(items)})")
        else:
            items = [a for a in ACTIONS if a["cat"] == self.current]
            self.title_lbl.configure(text=self.current)
        self._render(items)
        self.canvas.yview_moveto(0)   # volta a rolagem para o topo

    def _render(self, items):
        """Apaga os cartoes antigos e desenha os novos em grade de COLS colunas."""
        px = self.px
        for child in self.inner.winfo_children():
            child.destroy()
        if not items:
            tk.Label(self.inner, text="Nenhuma ação encontrada. Tente outra palavra, como disco, DNS ou driver.",
                     bg=BG, fg=MUTED, font=self.font(11)).grid(row=0, column=0, sticky="w", pady=px(20))
            return
        # Colunas de largura igual.
        for c in range(self.COLS):
            self.inner.columnconfigure(c, weight=1, uniform="col")
        for i, act in enumerate(items):
            self._card(act).grid(row=i // self.COLS, column=i % self.COLS, sticky="nsew", padx=px(6), pady=px(6))

    def _card(self, act):
        """Cria um cartao clicavel: faixa colorida + nome + descricao."""
        px = self.px
        card = tk.Frame(self.inner, bg=CARD, highlightthickness=1, highlightbackground=BORDER, cursor="hand2")
        stripe = tk.Frame(card, bg=RISK_COLORS[act["risk"]], width=px(5))    # faixa de risco
        stripe.pack(side="left", fill="y")
        body = tk.Frame(card, bg=CARD)
        body.pack(side="left", fill="both", expand=True, padx=px(14), pady=px(12))
        wrap = px(245)   # largura maxima do texto: com folga para nunca cortar na borda do cartao
        name = tk.Label(body, text=act["name"], bg=CARD, fg=TEXT, font=self.font(11, "bold"),
                        anchor="w", justify="left", wraplength=wrap)
        name.pack(fill="x")
        desc = tk.Label(body, text=act["desc"], bg=CARD, fg=MUTED, font=self.font(9),
                        anchor="w", justify="left", wraplength=wrap)
        desc.pack(fill="x", pady=(px(4), 0))

        parts = [card, body, name, desc]    # widgets que mudam de cor no hover

        def paint(color):
            for p in parts:
                p.configure(bg=color)

        # O clique funciona em qualquer parte do cartao (inclusive a faixa).
        for p in parts + [stripe]:
            p.bind("<Button-1>", lambda _e, a=act: self.on_click(a))
            p.bind("<Enter>", lambda _e: paint(CARD_HOVER))
            p.bind("<Leave>", lambda _e: paint(CARD))
        return card

    def on_click(self, act):
        """Fluxo do clique: confirmar -> perguntar dados -> executar."""
        # 1) Confirmacao Sim/Nao para acoes que alteram o sistema.
        if act.get("confirm"):
            if not messagebox.askyesno(act["name"], act["confirm"], icon="warning", parent=self):
                return

        # 2) Perguntas (ex.: IP/hostname). Cancelar ou valor invalido aborta a acao.
        values = {}
        for key, question in act["ask"]:
            v = simpledialog.askstring(act["name"], question, parent=self)
            if v is None:                       # usuario clicou em Cancelar
                return
            v = v.strip()
            if not HOST_RE.match(v):            # protecao contra injecao de comandos
                messagebox.showwarning(act["name"],
                                       "Valor inválido. Use apenas letras, números, ponto, hífen, dois-pontos ou sublinhado.",
                                       parent=self)
                return
            values[key] = v

        # 3) Executa e atualiza a barra de status (erros viram uma caixa de mensagem).
        try:
            run_action(act, values)
            self.status_var.set(f"{datetime.now():%H:%M:%S}  Executando: {act['name']}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro ao executar", f"Não foi possível executar a ação.\n\n{exc}", parent=self)

    def open_log(self):
        """Abre o arquivo de log no programa padrao (cria o arquivo se nao existir)."""
        try:
            if not LOG.exists():
                LOG.write_text("Log de Suporte TI\n", encoding="utf-8")
            os.startfile(str(LOG))  # type: ignore[attr-defined]  (so existe no Windows)
        except OSError as exc:
            messagebox.showerror("Log", str(exc), parent=self)


# ----------------------------------------------------------------------------
# 6. PONTO DE ENTRADA
# ----------------------------------------------------------------------------
def main():
    # Este programa usa comandos do Windows: em outros sistemas, avisa e sai.
    if os.name != "nt":
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Sistema não suportado", "Este programa funciona apenas no Windows.")
        return

    # Evita interface borrada em telas com escala acima de 100%.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # A maioria das acoes exige administrador: se nao for, reabre elevado.
    if not is_admin():
        elevate_and_exit()

    log("Programa iniciado")
    App().mainloop()          # loop da interface: roda ate a janela ser fechada
    log("Programa encerrado")


if __name__ == "__main__":
    main()
