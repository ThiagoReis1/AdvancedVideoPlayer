import cv2
import numpy as np

class EffectsProcessor:
    def __init__(self):
        self.effect_cache = {}  # Cache para efeitos
        self.vignette_mask = None
        self.vignette_frame_size = None  # Para verificar se o tamanho do frame mudou

    def clear_cache(self):
        """Limpa o cache de efeitos e máscaras"""
        self.effect_cache = {}
        self.vignette_mask = None
        self.vignette_frame_size = None

    def apply_effect_to_frame(self, frame, effect_type):
        """Aplica efeito ao frame (versão simplificada e estável)"""
        if effect_type == "none":
            return frame
        
        try:
            if effect_type == "bw":
                return self.apply_black_and_white(frame)
            elif effect_type == "negative":
                return self.apply_negative(frame)
            elif effect_type == "sepia":
                return self.apply_sepia(frame)
            elif effect_type == "posterize":
                return self.apply_posterize(frame)
            elif effect_type == "vignette":
                return self.apply_vignette(frame)
            else:
                return frame
        except Exception as e:
            print(f"Erro ao aplicar efeito {effect_type}: {e}")
            return frame

    def apply_black_and_white(self, frame):
        """Aplica efeito preto e branco a um frame"""
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def apply_negative(self, frame):
        """Aplica efeito negativo a um frame"""
        return 255 - frame

    def apply_sepia(self, frame):
        """Aplica efeito sépia a um frame (versão otimizada)"""
        try:
            # Usa LUT (Look-Up Table) para sépia, que é mais rápido
            sepia_kernel = np.array([[0.272, 0.534, 0.131],
                                    [0.349, 0.686, 0.168],
                                    [0.393, 0.769, 0.189]])
            
            # Aplicar transformação com OpenCV otimizado
            sepia_frame = cv2.transform(frame, sepia_kernel)
            
            # Clipar valores
            return np.clip(sepia_frame, 0, 255).astype(np.uint8)
        except Exception as e:
            print(f"Erro no efeito sépia: {e}")
            return frame

    def apply_posterize(self, frame):
        """Aplica efeito de posterização a um frame (versão otimizada)"""
        try:
            # Usa uma LUT (Look-Up Table) para posterizar - muito mais rápido
            levels = 5
            lut = np.zeros(256, dtype=np.uint8)
            for i in range(256):
                lut[i] = np.uint8(np.round(i / (255 / levels)) * (255 / levels))
            
            # Aplica a LUT em cada canal
            if len(frame.shape) == 3:  # Imagem colorida
                result = cv2.LUT(frame, lut)
            else:  # Imagem em escala de cinza
                result = cv2.LUT(frame, lut)
            
            return result
        except Exception as e:
            print(f"Erro no efeito posterize: {e}")
            return frame

    def apply_vignette(self, frame):
        """Aplica efeito de vinheta (versão simplificada)"""
        try:
            rows, cols = frame.shape[:2]
            
            # Verifica se já temos uma máscara para este tamanho de frame
            if self.vignette_mask is None or self.vignette_frame_size != (rows, cols):
                # Cria a máscara de vinheta de forma simplificada
                X, Y = np.ogrid[0:rows, 0:cols]
                center_x, center_y = rows / 2, cols / 2
                
                # Criar uma máscara circular
                dist_from_center = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
                # Normalizar pelo raio máximo
                max_dist = np.sqrt(center_x**2 + center_y**2)
                # Criar efeito de desvanecimento suave
                self.vignette_mask = np.clip(1 - dist_from_center/max_dist, 0, 1)
                self.vignette_frame_size = (rows, cols)
            
            # Aplicar máscara aos canais BGR
            result = frame.copy()
            for i in range(3):
                result[:, :, i] = result[:, :, i] * self.vignette_mask
                
            return result.astype(np.uint8)
        except Exception as e:
            print(f"Erro no efeito vinheta: {e}")
            return frame