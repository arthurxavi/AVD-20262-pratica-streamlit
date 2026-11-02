# Justificativa das métricas — Dashboard 2

## Métrica 1: total de ococrrências
- **Variável:** `Record_ID`
- **O que mede:** a quantidade total de chamadas de emergência e acidentes registrados no período
- **Por que foi escolhida:** é fundamental pra entender a dimensão dos dados sendo analisados 
- **Público-alvo:** gestores de trânsito e analistas de planejamento
- **Qual decisão pode ser apoiada por essa métrica?** distribuição de recursos de forma adequada
- **O que comunica ao público-alvo:** a carga total de trabalho ao longo do tempo

## Métrica 2: tempo médio de resposta
- **Variável:** Actual_Response_Time_min
- **O que mede:** o tempo médio que passa entre a chamada e a chegada da equipe de emergência
- **Por que foi escolhida:** é o melhor indicador da qualidade do serviço 
- **Público-alvo:** coordenadores de chamadas e orgãos reguladores de segurança
- **Qual decisão pode ser apoiada por essa métrica?** posicionamento melhor dos centros de apoio
- **O que comunica ao público-alvo:** o quão rápido uma equipe consegue chegar ao local da emergência

## Métrica 3: desvio da meta 
- **Variável:** Actual_Response_Time_min e Baseline_Expected_Response_Time_min
- **O que mede:** a diferença do tempo real de atendimento comparado ao tempo esperado(teórico)
- **Por que foi escolhida:** permite analisar a diferença entre o planejado e a realidade do serviço
- **Público-alvo:** coordenadores de chamadas/ coordenadores de estratégia
- **Qual decisão pode ser apoiada por essa métrica?** revisão para melhorar as rotas escolhidas para atender um chamado de emergência
- **O que comunica ao público-alvo:** o quanto que o tempo para atendimento de emergência real desvia do tempo teórico

## Métrica 4: taxa de chamados críticos
- **Variável:** Accident_Severity e Record_ID
- **O que mede:** o percentual de acidentes de extrema gravidade
- **Por que foi escolhida:** serve para prever a gravidade do acidente baseado nas infromações disponíveis
- **Público-alvo:** gestores de saúde e mobilidade urbana
- **Qual decisão pode ser apoiada por essa métrica?** fiscalização reforçada em trechos mais perigosos
- **O que comunica ao público-alvo:** o grau de severidade de acidentes viarios

## Métrica 5: tempo médio de interdição da via
- **Variável:** Road_Closure_Duration_min
- **O que mede:** o tempo médio que passa entre a chamada e a chegada da equipe de emergência
- **Por que foi escolhida:** é o melhor indicador do impacto que um acidente teve no fluxo do trânsito 
- **Público-alvo:** engenherios de tráfego
- **Qual decisão pode ser apoiada por essa métrica?** posicionamento estratégico de equipes em lugares onde interdições são mais duradouras
- **O que comunica ao público-alvo:** 
quanto tempo um local fica interditado (em média) após uma ocorrência viária