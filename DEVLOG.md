Comecei pelo enunciado pra entender o que tinha que funcionar de verdade. O trabalho pedia treinar um modelo, salvar ele, levar o arquivo para outro container e fazer uma consulta chegar na API.

Escolhi o dólar em relação ao real, USD/BRL, porque fica fácil explicar a unidade da previsão: quantos reais valem um dólar. Também era uma moeda que eu conseguiria procurar em fontes conhecidas, sem entrar nas diferenças entre várias corretoras de cripto.

Para o modelo escolhi o Prophet. Como os dados são uma sequência de datas e cotações, ele fazia sentido como ponto de partida e já tinha um jeito documentado de treinar, prever e salvar o modelo. Isso não quer dizer que seja o melhor modelo possível para câmbio, foi uma escolha para montar e testar o fluxo da atividade.

Resolvi usar um CSV como a base de dados do projeto, seguindo a sugestão do enunciado. Aqui eu só precisava guardar data e cotação para o treino, então um arquivo simples resolvia e ainda dava para montar ele no Docker.

O container de treino lê esse CSV. A API usa o modelo que saiu do treino, então cada pedido não precisa abrir a base inteira de novo. Isso também deixou mais fácil explicar o que cada container faz.

No começo olhei as fontes que o enunciado indicava, inclusive o Yahoo Finance. Primeiro montei uma base sintética só para conseguir desenvolver os containers e testar o caminho completo sem depender de internet. Usei IA para me ajudar a escrever o gerador e deixei uma semente fixa, assim o mesmo comando gerava o mesmo arquivo.

Essa primeira base tinha 978 linhas, de segunda a sexta. Conferi se as datas estavam em ordem, se havia repetição, campo vazio ou valor negativo, e comparei uma nova geração com o arquivo salvo usando cmp. Bateu. Só que ela não retirava feriados e, principalmente, eram valores inventados. Guardei isso como limitação desde o início.

Antes do treino fui na documentação do Prophet e vi que ele espera ds para data e y para o valor. Não mudei os nomes do CSV, porque data e cotacao_brl_por_usd são mais claros para quem abre o arquivo. Fiz a troca dos nomes só na hora de passar os dados para o modelo.

Separei treino e teste pela ordem do tempo: os primeiros 80% para treinar e os últimos 20% para avaliar. Não embaralhei, porque aí o modelo poderia aprender com datas que deveriam estar no futuro do teste. Nesse teste ele prevê o bloco inteiro sem receber os valores reais do meio do caminho.

Também coloquei uma referência simples que repete a última cotação do treino. Fiz isso porque um MAE sozinho não me diz muito; eu precisava ver se o Prophet ganhava pelo menos de uma regra básica.

Usei MAE para enxergar o erro médio em reais por dólar e RMSE para dar mais peso aos erros grandes. Não coloquei acurácia ou precisão de classificação, porque a saída é um número, não uma classe.

Na configuração inicial do Prophet deixei a sazonalidade anual ligada e as opções diária e semanal desligadas. O CSV tem uma cotação por data, sem informação de hora, e não tem uma cotação para todo sábado, domingo ou feriado. Foi um ponto de partida, não fiz uma busca para provar que esses parâmetros são os melhores.

Preferi rodar o treino no Docker porque o Prophet não estava instalado no Python local e o enunciado já aceitava treinamento em container. Na primeira consulta ao daemon apareceu erro de permissão no socket. Depois de executar com acesso permitido, vi que o Docker estava funcionando e segui por ele.

O primeiro docker build falhou antes mesmo de instalar as bibliotecas. O Docker não conseguiu resolver registry-1.docker.io por DNS. Repeti o build com --network=host e aí ele baixou a imagem Python e as dependências. Esse ajuste foi para o build nesse ambiente; o treino em si rodou com --network none.

No primeiro treino apareceu um aviso do Matplotlib tentando gravar em /.config/matplotlib, onde o usuário do container não tinha permissão. Coloquei MPLCONFIGDIR=/tmp/matplotlib no Dockerfile e rodei de novo. Também apareceu Importing plotly failed, mas eu não estava usando gráfico interativo e o treino terminou.

Com a base sintética, o Prophet deu MAE de 0,037886 e RMSE de 0,045343. A referência simples deu MAE de 0,052330 e RMSE de 0,069883. O resultado parecia bom, mas era em cima de uma série que a gente tinha criado, então eu não podia apresentar isso como capacidade de prever o dólar real.

Depois da avaliação, o código treina um segundo modelo com a base inteira para ser o modelo usado pela API. Salvei esse modelo em artifacts/model.json usando model_to_json do Prophet, porque o outro container consegue carregar esse formato com model_from_json. O script recarrega o JSON e faz uma previsão de exemplo para conferir que o arquivo não ficou só salvo, mas também pode ser usado.

O arquivo model.json fica numa pasta do computador que é montada nos dois containers. O primeiro container grava ali e termina. O segundo monta a mesma pasta só para leitura e carrega o modelo quando inicia. Escolhi isso para deixar claro por onde o artefato passa, sem precisar treinar de novo dentro da API nem copiar um resultado antigo para dentro da imagem.

Depois testei multistage build porque queria separar a instalação das bibliotecas da parte que realmente roda o treino. No Dockerfile, a etapa builder instala tudo num ambiente virtual em /opt/venv. A etapa runtime começa de outra imagem Python, pega esse ambiente e o script do treino. Achei que isso também podia deixar a imagem menor.

Medi os tamanhos depois do build e veio a surpresa: com multistage a imagem de treino ficou com 643 MB, enquanto a versão anterior tinha 605 MB. O build e o treino funcionaram, mas essa tentativa não economizou espaço. Mantive a divisão porque ficou mais claro o que é instalação e o que é execução, só não vou colocar redução de tamanho como vantagem que eu não consegui medir.

Fiz algo parecido no Dockerfile da API: ele pega o ambiente virtual da imagem de treino já construída e coloca o api.py numa etapa runtime. Por isso a ordem dos comandos importa, primeiro faço o build do treino e depois o da API. Escolhi reaproveitar o mesmo ambiente para não acabar usando outra versão do Prophet na hora de abrir o model.json. A IA me ajudou a montar esses Dockerfiles, e eu conferi a ideia reconstruindo as duas imagens e rodando os containers.

Usei IA para me ajudar a escrever o treino, os Dockerfiles e a API. Depois fui conferindo o que os arquivos realmente faziam com o CSV, os artefatos e os testes nos containers.

A IA também ajudou com os gráficos, os diagramas e a redação da documentação. Por isso mantive aqui os erros e as correções que aconteceram, porque o caminho real não foi tudo certinho de primeira.

No backend fiz uma API Python simples, sem adicionar um framework web, porque aqui eu só precisava receber uma data e devolver JSON. Coloquei GET /health para saber se o serviço subiu e carregou o modelo, e POST /predict para receber a data da previsão.

A resposta traz o valor previsto e os limites que o Prophet calcula. Ela não é salva automaticamente em outro arquivo; os arquivos que ficam guardados são o modelo e os resultados da avaliação.

Deixei o intervalo do Prophet em 80% para mostrar uma faixa junto com o valor central. Essa faixa é uma estimativa do próprio modelo, não uma promessa de onde a cotação real vai ficar.

A API rejeita JSON mal formado, data que não vem depois do fim do treino e fim de semana. Fiz essa validação para não devolver uma previsão para uma entrada que o código não sabe tratar direito. Ela ainda não conhece os feriados, então isso ficou como limite da implementação.

Quando subi a API, a primeira chamada com curl deu Operation not permitted por uma restrição do ambiente em que eu estava executando o teste. Repeti com acesso permitido. O /health respondeu 200, uma data válida no /predict respondeu 200 e um domingo voltou com 422. Isso confirmou a passagem do modelo do primeiro container para o segundo.

Também organizei os arquivos em src, docker, dados, artifacts e docs para não ficar código, CSV e resultado tudo misturado na raiz. Depois refiz os builds e rodei o treino e a API de novo. O CSV e as métricas da primeira versão continuaram iguais, então a mudança de caminho não tinha quebrado o fluxo.

Depois reli o enunciado e vi um problema maior: ele falava em dados históricos, e a minha base ainda era sintética. Ela foi útil para montar o projeto, mas não atendia bem essa parte da atividade. Resolvi trocar a base antes de fechar a documentação.

Com ajuda da IA, encontrei a série SGS 1 do Banco Central, que é a cotação diária de venda do dólar comercial. Preferi essa fonte ao Yahoo Finance porque o Banco Central descreve a série e a unidade de forma bem clara e oferece a consulta por API. Mantive USD/BRL e as mesmas colunas do CSV, assim não precisei mudar o contrato de entrada do treinamento.

Fixei o recorte de 02/01/2023 a 30/09/2026. Isso deixa registrado exatamente qual período entrou no teste e evita que cada pessoa rode o projeto com uma quantidade de dias diferente só porque baixou a cotação em outra data. O CSV fica na pasta do projeto, então para repetir o treino não precisa consultar a API de novo.

Na primeira tentativa de baixar os dados, o curl não conseguiu resolver o endereço da API do Banco Central. Repeti com acesso à rede e vieram 941 cotações. Não completei os dias sem cotação com valores inventados; por isso a quantidade de linhas é menor que na base sintética, que só pulava os fins de semana.

Usei IA para ajudar a escrever o novo script de coleta. Ele transforma as datas da resposta da API para AAAA-MM-DD, confere o período, a ordem, valores positivos e datas repetidas, e grava data e cotacao_brl_por_usd no CSV. Comparei as 941 linhas com a resposta baixada e guardei o SHA-256 do arquivo nas métricas, para saber exatamente qual CSV foi usado no treino.

Para baixar o mesmo recorte de novo, o comando é python3 src/baixar_cotacoes_usd_brl.py. Ele precisa de internet nessa hora. Depois que o CSV está salvo, o treinamento usa o arquivo local e roda sem rede.

Tirei o gerador e o CSV sintéticos do projeto para não ficar ambíguo qual base o container usa. Ajustei o Dockerfile de treino para apontar para usd_brl_historico.csv e mudei os rótulos da saída da API. A primeira execução ainda deixou a palavra sintéticos no arquivo de previsão de exemplo; achei esse pedaço esquecido no código, corrigi e rodei o treino de novo.

Com os dados do Banco Central, ficaram 753 linhas para treinar a avaliação e 188 para testar. O Prophet deu MAE de 0,165211 e RMSE de 0,217971. A referência simples deu MAE de 0,352412 e RMSE de 0,370360. Esses números são em reais por dólar, então o MAE do Prophet ficou perto de 16,5 centavos nesse bloco de teste.

O Prophet ganhou da referência nesse recorte, mas o gráfico mostra uma coisa que a média esconde. Perto do fim do teste, a previsão continua caindo enquanto a cotação observada volta a subir. Por isso eu não quero vender o resultado como um modelo confiável de mercado; com outro corte de tempo ele pode se comportar de outro jeito.

Refiz também o modelo final com todas as 941 cotações e substituí o model.json. Reconstruí a imagem da API e testei com os novos artefatos antes de colocá-los no projeto. O /health respondeu 200, o /predict devolveu 5,2152 reais por dólar para 06/10/2026 e um domingo continuou retornando 422. A previsão é experimental, não uma cotação do Banco Central.

No fim deixei dois desenhos UML com funções diferentes. O de arquitetura mostra o CSV, o container de treino, o model.json no host, o container da API e o cliente. O enunciado pede para explicar como o modelo chega na inferência, então esse desenho precisava mostrar a pasta compartilhada entre os containers.

O outro desenho é de sequência e foca só na consulta: carregar o modelo, receber a data, validar, prever e responder. Antes eu tinha misturado geração da base, treino e consulta no mesmo diagrama e ficou confuso. Deixei o tempo de cima para baixo e marquei os limites dos containers para mostrar que são processos separados.

Usei a IA como apoio para pensar e desenhar esses diagramas. Depois comparei as setas com o código e com os comandos que rodaram. O CSV só entra no container de treino; a consulta usa o model.json, que é a ligação entre as duas partes.

Atualizei o README, o gráfico, as métricas e os exemplos da API para mostrar a base histórica. O projeto funciona localmente e os comandos para repetir o treino e a consulta estão lá. Ainda falta registrar todos esses arquivos em commit e enviar para o GitHub antes da entrega final.
