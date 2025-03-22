import cv2
import time
import numpy as np

class VideoEngine:
    def __init__(self, effects_processor):
        self.effects_processor = effects_processor
        
        # Parâmetros de vídeo
        self.fps = 0
        self.total_frames = 0
        self.cap = None
        self.current_frame = 0
        self.video_length = 0  # em milissegundos
        
        # Parâmetros de reprodução
        self.playing = False
        self.start_time = None
        self.paused_elapsed = 0
        
        # Para buffer de frames
        self.frame_buffer = []
        self.buffer_start_frame = 0
        self.frames_per_batch = 24
        
        # Para monitoramento de FPS
        self.current_fps = 0
        self.last_frame_time = 0
        self.fps_update_interval = 1.0
        self.frames_count = 0
        
        # Efeito atual
        self.current_effect = "none"
        
        # Dimensões do vídeo
        self.container_width = 640
        self.container_height = 360

    def load_video_stream(self, file_path, width=640, height=360):
        """Carrega um fluxo de vídeo a partir de um arquivo"""
        # Libera cap antigo, se existir
        if self.cap is not None:
            self.cap.release()
        
        # Atualiza dimensões do container
        self.container_width = width or 640
        self.container_height = height or 360
        
        # Abre o vídeo
        self.cap = cv2.VideoCapture(file_path)
        if not self.cap.isOpened():
            print("Erro ao abrir o vídeo com OpenCV.")
            return
        
        # Extrai o FPS e o total de frames do vídeo
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0
        
        # Inicializa o buffer de frames
        self.frame_buffer = []
        self.buffer_start_frame = 0
        self.frames_per_batch = int(self.fps) if self.fps else 30  # Um segundo de frames
        
        # Carregar o primeiro lote de frames
        self.load_frame_batch(0)
        
        # Redefinir o controle de tempo
        self.reset_fps_counter()

    def load_frame_batch(self, start_frame):
        """Carrega um lote de frames a partir do índice especificado"""
        if self.cap is None or not self.cap.isOpened():
            return
        
        # Limpa o buffer atual
        self.frame_buffer.clear()
        
        # Define a posição inicial para o lote
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        self.buffer_start_frame = start_frame
        
        # Obtém dimensões uma única vez fora do loop
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Calcula a escala para manter a proporção
        scale = min(self.container_width / frame_width, self.container_height / frame_height)
        new_width = int(frame_width * scale)
        new_height = int(frame_height * scale)
        
        # Use um número fixo e razoável de frames por lote
        frames_to_load = min(self.frames_per_batch, self.total_frames - start_frame)
        
        for _ in range(frames_to_load):
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Redimensiona antes de aplicar efeito (mais eficiente)
            resized = cv2.resize(frame, (new_width, new_height))
            
            # Aplica o efeito selecionado
            processed_frame = self.effects_processor.apply_effect_to_frame(resized, self.current_effect)
            
            self.frame_buffer.append(processed_frame)

    def reload_frame_buffer(self):
        """Recarrega o buffer de frames atual com o novo efeito"""
        self.load_frame_batch(self.buffer_start_frame)

    def set_effect(self, effect):
        """Define o efeito a ser aplicado"""
        self.current_effect = effect

    def get_next_frame(self):
        """Obtém o próximo frame a ser exibido"""
        if not self.playing or self.cap is None:
            return None

        # Calcula o tempo decorrido e o frame correspondente
        elapsed_ms = self.get_elapsed_time()
        desired_frame = int(elapsed_ms * self.fps / 1000)

        # Verifica se chegou ao fim do vídeo
        if desired_frame >= self.total_frames:
            return None

        # Verifica se o frame está no buffer
        if desired_frame < self.buffer_start_frame or desired_frame >= self.buffer_start_frame + len(self.frame_buffer):
            # Carregar um novo lote
            batch_start = desired_frame
            # Tentar ir um pouco para trás para suavizar a transição
            batch_start = max(0, batch_start - 5)
            self.load_frame_batch(batch_start)
        
        # Obtém o frame do buffer
        buffer_index = desired_frame - self.buffer_start_frame
        if 0 <= buffer_index < len(self.frame_buffer):
            # Atualiza o frame atual
            self.current_frame = desired_frame
            
            # Atualiza o contador de FPS
            self.frames_count += 1
            current_time = time.time()
            time_diff = current_time - self.last_frame_time
            
            if time_diff >= self.fps_update_interval:
                self.current_fps = self.frames_count / time_diff
                self.frames_count = 0
                self.last_frame_time = current_time
                
            # Retorna o frame para exibição
            return self.frame_buffer[buffer_index]
        
        return None

    def get_current_frame(self):
        """Obtém o frame atual sem avançar"""
        if self.cap is None:
            return None
        
        # Verifica se o frame está no buffer
        buffer_index = self.current_frame - self.buffer_start_frame
        if 0 <= buffer_index < len(self.frame_buffer):
            return self.frame_buffer[buffer_index]
        
        # Se não estiver no buffer, carrega o lote correto
        self.load_frame_batch(max(0, self.current_frame - 5))
        
        # Tenta novamente
        buffer_index = self.current_frame - self.buffer_start_frame
        if 0 <= buffer_index < len(self.frame_buffer):
            return self.frame_buffer[buffer_index]
        
        return None

    def start_playback(self):
        """Inicia a reprodução do vídeo"""
        self.playing = True
        self.start_time = time.time() * 1000 - self.paused_elapsed
        self.reset_fps_counter()

    def pause(self):
        """Pausa a reprodução do vídeo"""
        if self.playing:
            self.playing = False
            self.paused_elapsed = self.get_elapsed_time()

    def resume(self):
        """Retoma a reprodução do vídeo"""
        if not self.playing:
            self.playing = True
            self.start_time = time.time() * 1000 - self.paused_elapsed
            self.reset_fps_counter()

    def stop(self):
        """Para a reprodução do vídeo"""
        self.playing = False
        self.current_frame = 0
        self.paused_elapsed = 0
        self.reset_fps_counter()

    def seek_to_time(self, ms):
        """Posiciona o vídeo no tempo especificado em milissegundos"""
        if self.cap is None:
            return
        
        # Calcula o frame correspondente ao tempo
        frame_index = int(ms * self.fps / 1000)
        frame_index = max(0, min(frame_index, self.total_frames - 1))
        
        # Atualiza o frame atual
        self.current_frame = frame_index
        
        # Carrega o lote correto de frames
        self.load_frame_batch(max(0, frame_index - 5))
        
        # Atualiza o tempo de pausa
        self.paused_elapsed = ms
        
        # Se estiver reproduzindo, atualiza o tempo de início
        if self.playing:
            self.start_time = time.time() * 1000 - ms

    def get_elapsed_time(self):
        """Obtém o tempo decorrido em milissegundos"""
        if not self.playing:
            return self.paused_elapsed
        
        current_time = time.time() * 1000
        return current_time - self.start_time

    def reset_fps_counter(self):
        """Reinicia o contador de FPS"""
        self.last_frame_time = time.time()
        self.frames_count = 0
        self.current_fps = 0
