# Central de Suporte

> **O canivete suíço do suporte técnico no Windows, a um clique de distância.**

![Versão](https://img.shields.io/badge/vers%C3%A3o-1.0%20(testes)-orange)
![Plataforma](https://img.shields.io/badge/plataforma-Windows%2010%20%7C%2011-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-yellow)
![Status](https://img.shields.io/badge/status-em%20testes-red)

> ⚠️ **Versão de testes 1.0.** O programa está em fase de testes. Use com atenção, de preferência em máquinas de teste primeiro, e envie suas sugestões e problemas pela aba **Issues**.

---

## O que é?

Quem trabalha com suporte técnico conhece a rotina: abrir o prompt, lembrar o comando certo, digitar `sfc /scannow`, depois `DISM`, depois limpar o DNS, depois verificar o disco... em cada máquina, todos os dias.

A **Central de Suporte** reúne essas rotinas em uma única janela. Você escolhe a ação com um clique, o programa abre um terminal com o comando já em execução e você acompanha o resultado na tela. Sem decorar comandos e sem digitar nada além do necessário.

É um programa em **Python com interface gráfica minimalista** (Tkinter), sem dependências externas, que pode ser empacotado em um único `.exe` portátil.

## Destaques

- **54 ações** organizadas em 7 categorias, acessíveis com o mouse.
- **Terminal automático:** cada ação abre o `cmd` já com o comando rodando, e a janela fica aberta para você ler o resultado.
- **Saúde do disco (HDD e SSD):** relatório com status, temperatura, desgaste, horas de uso e erros, com veredito **OK** ou **Atenção**.
- **Reparo e limpeza:** reinício do driver de vídeo, limpeza de caches (GPU, ícones, navegadores), reset da Microsoft Store e mais.
- **Inventário da máquina:** coleta hostname, usuário, rede, discos, CPU, RAM e versão do Windows e salva um `.txt` na área de trabalho, pronto para colar em um chamado.
- **Busca rápida:** digite "dns", "disco" ou "driver" e encontre a ação em todas as categorias.
- **Portátil:** a pasta do programa pode ser arrastada para qualquer lugar, inclusive um pendrive.
- **Seguro por padrão:** ações que alteram o sistema pedem confirmação antes de rodar.

## Categorias e ações

A cor da faixa lateral de cada cartão indica o tipo da ação: **azul** para diagnóstico, **âmbar** para ações que alteram o sistema e **vermelho** para ações sensíveis.

### Disco e sistema
| Ação | O que faz |
|---|---|
| Verificar disco (CHKDSK) | Verifica e corrige erros do sistema de arquivos |
| Reparar arquivos do sistema (SFC) | Repara arquivos protegidos do Windows |
| Reparar imagem do Windows (DISM) | CheckHealth, ScanHealth e RestoreHealth em sequência |
| Limpar arquivos temporários | Limpa `%TEMP%` e `C:\Windows\Temp` |
| Otimizar / desfragmentar disco | Desfragmenta HDD e faz TRIM em SSD |
| Diagnóstico de memória RAM | Abre o Diagnóstico de Memória do Windows |
| Teste de velocidade do disco | Mede leitura e escrita com o WinSAT |

### Saúde do disco
| Ação | O que faz |
|---|---|
| Relatório de saúde (HDD e SSD) | Status, temperatura, desgaste, horas ligado e erros, com veredito |
| Previsão de falha (SMART) | Consulta o alerta de falha iminente do firmware |
| Identificar HDD ou SSD e TRIM | Mostra o tipo de cada disco e o status do TRIM |
| Espaço por partição | Tamanho, espaço livre e saúde de cada volume |
| Verificação online | `chkdsk /scan`, somente leitura |
| Erros de disco nos eventos | Erros e avisos de disco dos últimos 30 dias |
| Retrim em SSD | Reenvia o TRIM para recuperar desempenho |

### Rede
| Ação | O que faz |
|---|---|
| Teste de rede (ping e DNS) | Ping em 1.1.1.1 e 8.8.8.8 e consulta DNS |
| Testar comunicação com uma máquina | Ping e resolução de nome de um IP ou hostname |
| Rota até o destino (tracert) | Mostra os saltos até o destino |
| Testar portas comuns | 3389, 445, 80, 443, 53 e 22, com latência |
| Limpar cache DNS | `ipconfig /flushdns` |
| Limpar e registrar DNS novamente | Flush seguido de registerdns |
| Resetar pilha de rede (Winsock/IP) | Reset de Winsock e IP (requer reinício) |
| IPConfig detalhado | `ipconfig /all` |
| Renovar IP e limpar cache ARP | Release, renew e limpeza do ARP |
| Conexões ativas (netstat) | Portas abertas e PID de cada conexão |

### Windows
| Ação | O que faz |
|---|---|
| Gerenciador de Tarefas | Abre o Gerenciador de Tarefas |
| Visualizar logs de eventos | Abre o Visualizador de Eventos |
| Gerenciador de dispositivos (ocultos) | Abre já mostrando dispositivos ocultos |
| Windows Update (buscar/abrir) | Dispara a busca e abre a tela de atualizações |
| Resetar Windows Update | Reinicia serviços e limpa o cache de atualizações |
| Firewall: status, ativar e desativar | Gerencia o Firewall do Windows |
| Limpar fila de impressão | Reinicia o spooler e apaga trabalhos travados |

### Reparo e limpeza
| Ação | O que faz |
|---|---|
| Reiniciar driver de vídeo | Desativa e reativa o adaptador de vídeo |
| Limpar cache de shaders da GPU | Limpa caches de DirectX, NVIDIA e AMD |
| Limpar cache de ícones e miniaturas | Corrige ícones em branco ou errados |
| Reiniciar o Explorer | Reinicia a barra de tarefas e a área de trabalho |
| Resetar cache da Microsoft Store | Executa o `wsreset` |
| Re-registrar apps do Windows | Registra novamente os apps do sistema |
| Reiniciar serviço de áudio | Quando o som some |
| Limpar cache de Edge e Chrome | Limpa o cache sem tocar em senhas e favoritos |
| Esvaziar lixeira | Esvazia a lixeira de todas as unidades |

### Informações
| Ação | O que faz |
|---|---|
| Inventário da máquina (.txt) | Relatório completo salvo na área de trabalho |
| Informações do sistema | `systeminfo` |
| Informações de hardware | Placa-mãe, BIOS, CPU, memórias, vídeo e discos |
| Chave de produto do Windows | Chave OEM da BIOS e estado da licença |
| Status da bateria | Carga atual e relatório de saúde da bateria |

### Configurações
| Ação | O que faz |
|---|---|
| Criar ponto de restauração | Cria um ponto antes de mudanças grandes |
| Sincronizar hora | Ressincroniza o relógio com o servidor de hora |
| Backup de drivers | Exporta os drivers para `C:\BackupDrivers` |
| Atualizar programas (winget) | `winget upgrade --all` |
| Forçar políticas de grupo | `gpupdate /force` |
| Ativar/desativar conta Administrador local | Gerencia a conta interna de administrador |

## Requisitos

- Windows 10 ou 11
- Permissão de administrador (o programa pede ao abrir)
- Para executar o código-fonte ou compilar: Python 3.9 ou superior, sem bibliotecas externas

## Como usar

### Opção 1: executar o `.exe`
1. Baixe a pasta do programa.
2. Dê dois cliques em `CentralSuporte.exe` e aceite o aviso de administrador.
3. Escolha uma categoria, clique em uma ação e acompanhe o terminal.

### Opção 2: executar o código-fonte
```bat
python central_suporte.py
```
O programa pede elevação de administrador sozinho.

### Opção 3: gerar o seu próprio `.exe`
1. Instale o Python em [python.org](https://www.python.org/downloads/), marcando **Add python.exe to PATH**.
2. Deixe o `central_suporte.py` e o `gerar_exe.bat` na mesma pasta e execute o `gerar_exe.bat`.
3. O gerador cria a pasta **Central de Suporte** na área de trabalho, compila o `CentralSuporte.exe` dentro dela e move os arquivos para lá.

Estrutura depois da instalação:

```
Central de Suporte\
├── CentralSuporte.exe      programa pronto para usar
├── central_suporte.py      código-fonte
├── gerar_exe.bat           gerador (rode daqui para recompilar)
└── compilacao\             arquivos temporários da compilação
```

A pasta é portátil: você pode movê-la para onde quiser, e o `.exe` continua funcionando.

## Segurança e boas práticas

- **Confirmação antes de agir:** ações que alteram o sistema mostram um aviso antes de executar.
- **Entradas validadas:** IPs e hostnames digitados aceitam apenas caracteres seguros, o que impede injeção de comandos.
- **Log de atividades:** cada ação executada é registrada em `%TEMP%\suporte_ti.log`, e o link **Abrir arquivo de log** fica na barra lateral.
- **Transparência:** o código-fonte é aberto e comentado, e o terminal mostra exatamente o que está sendo executado.
- **Recomendação:** antes de mudanças maiores (DISM, reset de rede, remoção de caches), crie um ponto de restauração pela própria ferramenta.

### Aviso sobre antivírus
Executáveis gerados com PyInstaller, especialmente os que mexem em serviços, firewall e drivers, podem ser sinalizados pelo Windows Defender ou pelo SmartScreen como falso positivo. Se isso acontecer, use **Mais informações > Executar assim mesmo** ou adicione uma exceção. Se preferir, execute o código-fonte diretamente.

## Limitações da versão de testes

- Algumas funções dependem do hardware e da versão do Windows. Por exemplo, nem todo disco expõe SMART, e o `winget` pode não existir em instalações mais antigas do Windows 10.
- Para ações que mexem no sistema, o programa depende do resultado dos comandos nativos do Windows e mostra no terminal o retorno de cada um.
- Ainda não foi validado em todas as versões e edições do Windows.

## Como contribuir

Sugestões, correções e novas funções são bem-vindas:

1. Abra uma **Issue** descrevendo o problema ou a ideia (informe a versão do Windows).
2. Faça um **fork**, crie uma branch e envie um **Pull Request**.

Para adicionar uma nova ação, basta incluir uma chamada `add(...)` na seção do catálogo do `central_suporte.py`, indicando a categoria, o nome, a descrição e o comando. A interface a exibe automaticamente.

## Aviso legal

Este software é fornecido **"como está"**, sem garantias, e se encontra em fase de testes. Algumas ações alteram configurações do sistema, apagam arquivos temporários ou reiniciam serviços. Você é responsável pelo uso que fizer dele. Teste em um ambiente seguro e mantenha backups.

## Licença

Defina aqui a licença do projeto (por exemplo, MIT) e adicione o arquivo `LICENSE` ao repositório.

---

**Central de Suporte v1.0 (testes).** Feito para quem tem muita máquina para atender e pouco tempo para digitar comando.
