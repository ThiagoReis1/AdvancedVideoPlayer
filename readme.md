# Reprodutor de Vídeo Avançado com Efeitos

Um player de vídeo implementado em Python com capacidade de aplicar efeitos visuais em tempo real aos vídeos reproduzidos, utilizando uma combinação do VLC para reprodução padrão e OpenCV para processamento de imagem.

## 📋 Visão Geral

Este projeto implementa um reprodutor de vídeo com as seguintes funcionalidades:
- Reprodução de vídeos em formato MP4 e outros formatos suportados
- Interface gráfica de usuário amigável usando Tkinter
- Aplicação de efeitos visuais em tempo real (preto e branco, negativo, sépia, posterização, vinheta)
- Controles básicos de reprodução (play/pause, stop, controle de volume)
- Exibição de informações de FPS (frames por segundo)
- Barra de progresso para navegação no vídeo
- Exportação de vídeos com efeitos aplicados

O sistema alterna entre dois modos de reprodução:
1. **Modo VLC:** para reprodução normal de vídeo sem efeitos
2. **Modo OpenCV:** para reprodução com efeitos visuais aplicados em tempo real

## 🧩 Arquitetura do Sistema

O projeto é dividido em cinco módulos principais:

1. **main-script.py**
   - Ponto de entrada da aplicação
   - Inicializa a interface gráfica e o reprodutor de vídeo

2. **video_player.py**
   - Implementa a interface gráfica do usuário
   - Gerencia a interação com o usuário (botões, sliders, etc.)
   - Coordena os diferentes modos de reprodução (VLC e OpenCV)

3. **video_engine.py**
   - Motor de reprodução de vídeo para o modo OpenCV
   - Gerencia o buffer de frames, aplicação de efeitos e sincronização
   - Calcula e monitora informações de FPS

4. **effects_processor.py**
   - Processamento e aplicação de efeitos visuais
   - Implementa diferentes algoritmos de efeitos (preto e branco, sépia, etc.)
   - Otimizado para processamento eficiente em tempo real

5. **video_exporter.py**
   - Gerencia a exportação de vídeos com efeitos aplicados
   - Implementa sistema de fila para processamento de múltiplas exportações
   - Mantém o áudio original nos vídeos exportados
   - Fornece interface para monitoramento e controle do processo de exportação

## 🚀 Requisitos

- Python 3.6+
- Bibliotecas:
  - tkinter
  - python-vlc
  - OpenCV (cv2)
  - NumPy
  - PIL (Pillow)
- FFmpeg (opcional, para melhor suporte à exportação com áudio)

## 📁 Arquivo de Requisitos (requirements.txt)

Este projeto utiliza um arquivo chamado **requirements.txt** para facilitar a instalação das bibliotecas necessárias. Nele, estão listadas as seguintes dependências:

- **opencv-python**: Biblioteca para processamento de vídeo e aplicação de efeitos com OpenCV.
- **numpy**: Biblioteca para computação numérica e manipulação eficiente de arrays, utilizada principalmente para o processamento dos frames de vídeo.
- **python-vlc**: Interface em Python para o VLC Media Player, responsável pela reprodução padrão dos vídeos.
- **Pillow**: Biblioteca para processamento de imagens, utilizada na conversão de frames para formatos compatíveis com a interface Tkinter.

### Como instalar as bibliotecas usando o requirements.txt

Para instalar todas as dependências listadas no arquivo **requirements.txt**, execute o seguinte comando no terminal dentro do diretório do projeto:

```bash
pip install -r requirements.txt
