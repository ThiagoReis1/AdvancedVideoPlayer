import sys
import time
import tkinter as tk
from tkinter import filedialog, ttk
import vlc
from PIL import Image, ImageTk
import cv2
import os
import threading
import shutil
from effects_processor import EffectsProcessor
from video_engine import VideoEngine
from video_exporter import VideoExporter

class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Player de Vídeo Avançado")
        self.root.configure(bg="#2C2C2C")

        # Instanciar o processador de efeitos e o motor de vídeo
        self.effects_processor = EffectsProcessor()
        self.ffmpeg_available = self.check_ffmpeg_availability()
        self.video_engine = VideoEngine(self.effects_processor)

        # Variáveis de controle
        self.mode = "vlc"  # "vlc" para modo normal ou "opencv" para modo com efeito
        self.current_file = None
        self.last_position = 0
        self.position_set = False

        # Instância do VLC e players para áudio/vídeo
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.audio_player = self.instance.media_player_new()

        # Configurar a interface gráfica
        self.setup_ui()

        # Instanciar o exportador e vincular os botões de exportação
        self.exporter = VideoExporter(self)
        self.btn_generate.config(command=lambda: self.exporter.queue_video_export())
        self.btn_cancel_all.config(command=lambda: self.exporter.cancel_all_exports())

        # Iniciar atualização periódica do slider
        self.update_slider()

    def setup_ui(self):
        # Área de vídeo
        self.video_frame = tk.Frame(self.root, width=640, height=360, bg="black")
        self.video_frame.pack_propagate(False)
        self.video_frame.pack(padx=10, pady=10)

        self.video_label = None

        # Configurar o player VLC para exibir o vídeo na área designada
        self.root.update()
        if sys.platform.startswith('linux'):
            self.player.set_xwindow(self.video_frame.winfo_id())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winfo_id())
        elif sys.platform == "darwin":
            self.player.set_nsobject(self.video_frame.winfo_id())

        # Frame de informações (FPS)
        self.info_frame = tk.Frame(self.root, bg="#2C2C2C", width=200, height=360)
        self.info_frame.pack_propagate(False)
        self.info_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        self.original_fps_label = tk.Label(self.info_frame, text="FPS Original: --",
                                           bg="#2C2C2C", fg="white", font=("Arial", 10))
        self.original_fps_label.pack(pady=(20, 5), anchor="w")

        self.current_fps_label = tk.Label(self.info_frame, text="FPS Atual: --",
                                          bg="#2C2C2C", fg="white", font=("Arial", 10))
        self.current_fps_label.pack(pady=5, anchor="w")

        # Controles de reprodução
        control_frame = tk.Frame(self.root, bg="#2C2C2C")
        control_frame.pack(pady=5)

        btn_open = tk.Button(control_frame, text="Escolher Vídeo",
                             command=self.open_file, bg="#4A4A4A", fg="white", relief=tk.FLAT)
        btn_open.pack(side=tk.LEFT, padx=5)

        btn_play_pause = tk.Button(control_frame, text="Play/Pause",
                                   command=self.toggle_play_pause, bg="#4A4A4A", fg="white", relief=tk.FLAT)
        btn_play_pause.pack(side=tk.LEFT, padx=5)

        btn_stop = tk.Button(control_frame, text="Stop",
                             command=self.stop_video, bg="#4A4A4A", fg="white", relief=tk.FLAT)
        btn_stop.pack(side=tk.LEFT, padx=5)

        btn_effects = tk.Button(control_frame, text="Escolher Efeitos",
                                command=self.open_effects_window, bg="#4A4A4A", fg="white", relief=tk.FLAT)
        btn_effects.pack(side=tk.LEFT, padx=5)

        # Controle de volume
        volume_frame = tk.Frame(control_frame, bg="#2C2C2C")
        volume_frame.pack(side=tk.LEFT, padx=10)
        volume_label = tk.Label(volume_frame, text="Volume", bg="#2C2C2C", fg="white")
        volume_label.pack(side=tk.LEFT, padx=(0, 5))
        self.volume_var = tk.IntVar(value=50)
        self.volume_slider = tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                      variable=self.volume_var, command=self.volume_changed,
                                      bg="#2C2C2C", fg="white", troughcolor="#4A4A4A",
                                      highlightthickness=0, width=8, length=100)
        self.volume_slider.pack(side=tk.LEFT)

        # Slider de tempo
        self.scale_var = tk.IntVar()
        self.slider = tk.Scale(self.root, variable=self.scale_var, from_=0, to=100,
                               orient=tk.HORIZONTAL, length=640, command=self.slider_moved,
                               bg="#2C2C2C", fg="white", troughcolor="#4A4A4A",
                               highlightthickness=0, width=8)
        self.slider.pack(pady=5)
        self.slider.bind("<ButtonRelease-1>", self.slider_released)
        self.time_label = tk.Label(self.root, text="00:00 / 00:00", bg="#2C2C2C", fg="white")
        self.time_label.pack()

        # Seletor de efeitos
        self.effect_var = tk.StringVar(value="none")
        self.updating_slider = False

        # Botão para gerar vídeo (ação definida pela classe VideoExporter)
        self.btn_generate = tk.Button(control_frame, text="Gerar Vídeo",
                                      command=None, bg="#4A4A4A", fg="white", relief=tk.FLAT)
        self.btn_generate.pack(side=tk.LEFT, padx=5)

        # Área para fila de exportação
        self.export_frame = tk.Frame(self.root, bg="#2C2C2C")
        self.export_frame.pack(fill=tk.X, padx=10, pady=5)

        export_label = tk.Label(self.export_frame, text="Fila de Exportação:",
                                bg="#2C2C2C", fg="white", font=("Arial", 10, "bold"))
        export_label.pack(side=tk.LEFT, pady=5)

        self.btn_cancel_all = tk.Button(self.export_frame, text="Cancelar Todas",
                                        command=None, bg="#4A4A4A", fg="white",
                                        relief=tk.FLAT, state=tk.DISABLED)
        self.btn_cancel_all.pack(side=tk.RIGHT, padx=5)

        self.queue_container = tk.Frame(self.root, bg="#2C2C2C")
        self.queue_container.pack(fill=tk.X, padx=10)

    def format_time(self, ms):
        """Formata milissegundos para o formato HH:MM:SS ou MM:SS"""
        total_seconds = ms // 1000
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"

    def open_file(self):
        """Abre um arquivo de vídeo"""
        file_path = filedialog.askopenfilename(title="Selecione um arquivo de vídeo",
                                               filetypes=[("Arquivos MP4", "*.mp4"), ("Todos os arquivos", "*.*")])
        if file_path:
            self.effects_processor.clear_cache()
            self.current_file = file_path

            temp_cap = cv2.VideoCapture(file_path)
            if temp_cap.isOpened():
                fps = temp_cap.get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    self.video_engine.fps = fps
                    self.original_fps_label.config(text=f"FPS Original: {fps:.2f}")
                temp_cap.release()

            if self.effect_var.get() != "none":
                self.mode = "opencv"
                self.video_engine.load_video_stream(file_path, self.video_frame.winfo_width(), self.video_frame.winfo_height())
                total_time = int((self.video_engine.total_frames / self.video_engine.fps) * 1000)
                self.slider.config(to=total_time)
                self.time_label.config(text=f"00:00 / {self.format_time(total_time)}")
                media = self.instance.media_new(file_path)
                media.add_option(":no-video")
                self.audio_player.set_media(media)
                self.audio_player.play()
                self.root.after(50, self.start_opencv_playback)
            else:
                self.mode = "vlc"
                if self.video_label is not None:
                    self.video_label.pack_forget()
                media = self.instance.media_new(file_path)
                self.player.set_media(media)
                self.player.play()
                self.current_fps_label.config(text="FPS Atual: 0.00")
                self.root.after(100, self.set_video_length)

    def start_opencv_playback(self):
        """Inicia a reprodução utilizando OpenCV"""
        self.video_engine.start_playback()

        if self.video_label is None:
            self.video_label = tk.Label(self.video_frame)
            self.video_label.pack(fill=tk.BOTH, expand=True)
        else:
            self.video_label.pack()

        self.show_next_frame()

    def show_next_frame(self):
        """Exibe o próximo frame processado"""
        if self.mode != "opencv" or not self.video_engine.playing:
            return

        frame = self.video_engine.get_next_frame()
        if frame is not None:
            if len(frame.shape) == 2:
                img = Image.fromarray(frame).convert('RGB')
            else:
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            photo = ImageTk.PhotoImage(image=img)
            self.video_label.config(image=photo)
            self.video_label.image = photo

            self.update_fps_display()

            elapsed_ms = self.video_engine.get_elapsed_time()
            desired_frame = self.video_engine.current_frame

            if desired_frame % 4 == 0:
                total_time = int((self.video_engine.total_frames / self.video_engine.fps) * 1000)
                self.scale_var.set(int(elapsed_ms))
                self.time_label.config(text=f"{self.format_time(int(elapsed_ms))} / {self.format_time(total_time)}")

            frame_interval = 1000 / self.video_engine.fps
            next_frame_time = (desired_frame + 1) * frame_interval
            time_to_wait = max(1, min(int(frame_interval), int(next_frame_time - elapsed_ms)))
            self.root.after(time_to_wait, self.show_next_frame)
        else:
            self.stop_video()

    def update_fps_display(self):
        """Atualiza o FPS atual exibido"""
        fps = self.video_engine.current_fps
        if fps > 0:
            self.current_fps_label.config(text=f"FPS Atual: {fps:.2f}")
        else:
            self.current_fps_label.config(text="FPS Atual: 0.00")

    def set_video_length(self):
        """Configura o comprimento do vídeo no modo VLC"""
        length = self.player.get_length()
        if length > 0:
            self.video_engine.video_length = length
            self.slider.config(to=length)

            fps_detected = False
            if self.mode == "vlc":
                media = self.player.get_media()
                if media:
                    media_tracks = media.tracks_get()
                    for track in media_tracks:
                        if track.type == vlc.TrackType.video:
                            if track.video.frame_rate_num > 0 and track.video.frame_rate_den > 0:
                                original_fps = track.video.frame_rate_num / track.video.frame_rate_den
                                self.video_engine.fps = original_fps
                                self.original_fps_label.config(text=f"FPS Original: {original_fps:.2f}")
                                fps_detected = True
                                break
                    media_tracks.release()

            if not fps_detected:
                if self.video_engine.total_frames > 0 and length > 0:
                    estimated_fps = self.video_engine.total_frames / (length / 1000.0)
                    if estimated_fps > 0:
                        self.video_engine.fps = estimated_fps
                        self.original_fps_label.config(text=f"FPS Original: {estimated_fps:.2f}")

            self.video_engine.reset_fps_counter()
            self.update_vlc_fps()
        else:
            self.root.after(100, self.set_video_length)

    def update_vlc_fps(self):
        """Atualiza o FPS no modo VLC periodicamente"""
        if self.mode == "vlc":
            if self.player.is_playing():
                self.current_fps_label.config(text=f"FPS Atual: {self.video_engine.fps:.2f}")
            else:
                self.current_fps_label.config(text="FPS Atual: 0.00")
        if self.mode == "vlc":
            self.root.after(1000, self.update_vlc_fps)

    def toggle_play_pause(self):
        """Alterna entre reprodução e pausa"""
        if self.mode == "vlc":
            if self.player.is_playing():
                self.player.pause()
                self.current_fps_label.config(text="FPS Atual: 0.00")
            else:
                self.player.play()
                self.video_engine.reset_fps_counter()
        elif self.mode == "opencv":
            if self.video_engine.playing:
                self.video_engine.pause()
                self.audio_player.pause()
                self.current_fps_label.config(text="FPS Atual: 0.00")
            else:
                self.video_engine.resume()
                self.audio_player.play()
                self.show_next_frame()

    def stop_video(self):
        """Para a reprodução do vídeo"""
        if self.mode == "vlc":
            self.player.stop()
            self.scale_var.set(0)
            self.time_label.config(text="00:00 / 00:00")
            self.current_fps_label.config(text="FPS Atual: 0.00")
        elif self.mode == "opencv":
            self.video_engine.stop()
            self.audio_player.stop()
            self.slider.set(0)
            self.time_label.config(text="00:00 / 00:00")
            self.current_fps_label.config(text="FPS Atual: 0.00")
            if self.video_label is not None:
                self.video_label.config(image='')

    def volume_changed(self, val):
        """Ajusta o volume da reprodução"""
        volume = int(val)
        if self.mode == "vlc":
            self.player.audio_set_volume(volume)
        else:
            self.audio_player.audio_set_volume(volume)

    def update_slider(self):
        """Atualiza a posição do slider conforme o tempo do vídeo"""
        if self.mode == "vlc" and self.player.is_playing():
            current_time = self.player.get_time()
            if not self.updating_slider:
                self.scale_var.set(current_time)
            self.time_label.config(text=f"{self.format_time(current_time)} / {self.format_time(self.video_engine.video_length)}")
        elif self.mode == "opencv":
            current_time = self.audio_player.get_time() if self.audio_player.get_time() >= 0 else 0
            total_time = int((self.video_engine.total_frames / self.video_engine.fps) * 1000) if self.video_engine.fps else 0
            if not self.updating_slider:
                self.scale_var.set(current_time)
            self.time_label.config(text=f"{self.format_time(current_time)} / {self.format_time(total_time)}")
        self.root.after(500, self.update_slider)

    def slider_moved(self, val):
        """Callback ao mover o slider"""
        self.updating_slider = True

    def slider_released(self, event):
        """Callback ao soltar o slider"""
        new_time = self.scale_var.get()
        if self.mode == "vlc":
            self.player.set_time(new_time)
        elif self.mode == "opencv":
            self.audio_player.set_time(new_time)
            self.video_engine.seek_to_time(new_time)
            if not self.video_engine.playing and self.video_label is not None:
                frame = self.video_engine.get_current_frame()
                if frame is not None:
                    if len(frame.shape) == 2:
                        img = Image.fromarray(frame).convert('RGB')
                    else:
                        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    photo = ImageTk.PhotoImage(image=img)
                    self.video_label.config(image=photo)
                    self.video_label.image = photo
        self.updating_slider = False

    def open_effects_window(self):
        """Abre a janela de seleção de efeitos ou traz a existente para frente."""
        # Verifica se a janela já foi criada e se ainda existe
        if hasattr(self, 'effects_window') and self.effects_window is not None and self.effects_window.winfo_exists():
            self.effects_window.lift()  # Traz a janela para frente
            return

        # Cria a janela de efeitos e armazena a referência
        self.effects_window = tk.Toplevel(self.root)
        self.effects_window.title("Escolha de Efeitos")
        self.effects_window.configure(bg="#2C2C2C")
        self.effects_window.resizable(False, False)

        # Define um protocolo para limpar a referência ao fechar a janela
        def on_close():
            self.effects_window.destroy()
            self.effects_window = None

        self.effects_window.protocol("WM_DELETE_WINDOW", on_close)

        # Criação dos Radiobuttons
        rb_none = tk.Radiobutton(self.effects_window, text="Sem Efeito",
                                variable=self.effect_var, value="none",
                                bg="#2C2C2C", fg="white", selectcolor="#4A4A4A")
        rb_none.pack(anchor='w', padx=10, pady=5)

        rb_bw = tk.Radiobutton(self.effects_window, text="Preto e Branco",
                            variable=self.effect_var, value="bw",
                            bg="#2C2C2C", fg="white", selectcolor="#4A4A4A")
        rb_bw.pack(anchor='w', padx=10, pady=5)

        rb_negative = tk.Radiobutton(self.effects_window, text="Negativo",
                                    variable=self.effect_var, value="negative",
                                    bg="#2C2C2C", fg="white", selectcolor="#4A4A4A")
        rb_negative.pack(anchor='w', padx=10, pady=5)

        rb_sepia = tk.Radiobutton(self.effects_window, text="Sépia",
                                variable=self.effect_var, value="sepia",
                                bg="#2C2C2C", fg="white", selectcolor="#4A4A4A")
        rb_sepia.pack(anchor='w', padx=10, pady=5)

        rb_posterize = tk.Radiobutton(self.effects_window, text="Posterização",
                                    variable=self.effect_var, value="posterize",
                                    bg="#2C2C2C", fg="white", selectcolor="#4A4A4A")
        rb_posterize.pack(anchor='w', padx=10, pady=5)

        rb_vignette = tk.Radiobutton(self.effects_window, text="Vinheta",
                                    variable=self.effect_var, value="vignette",
                                    bg="#2C2C2C", fg="white", selectcolor="#4A4A4A")
        rb_vignette.pack(anchor='w', padx=10, pady=5)

        btn_apply = tk.Button(self.effects_window, text="Aplicar",
                            command=lambda: self.apply_effect(self.effect_var.get()),
                            bg="#4A4A4A", fg="white", relief=tk.FLAT)
        btn_apply.pack(padx=10, pady=10)


    def apply_effect(self, effect):
        """Aplica o efeito selecionado ao vídeo"""
        if self.current_file:
            self.video_engine.set_effect(effect)

            current_position = 0
            was_playing = False

            if self.mode == "vlc" and self.player.is_playing():
                current_position = self.player.get_time()
                was_playing = True
            elif self.mode == "vlc" and not self.player.is_playing():
                current_position = self.player.get_time()
                was_playing = False
            elif self.mode == "opencv":
                current_position = self.video_engine.get_elapsed_time()
                was_playing = self.video_engine.playing

            self.last_position = current_position

            if effect != "none" and self.mode != "opencv":
                self.player.stop()
                self.mode = "opencv"
                self.video_engine.load_video_stream(self.current_file, self.video_frame.winfo_width(), self.video_frame.winfo_height())

                if self.video_engine.fps > 0:
                    self.original_fps_label.config(text=f"FPS Original: {self.video_engine.fps:.2f}")

                media = self.instance.media_new(self.current_file)
                media.add_option(":no-video")
                self.audio_player.set_media(media)
                self.audio_player.play()

                if current_position > 0:
                    self.audio_player.set_time(current_position)
                    self.video_engine.seek_to_time(current_position)

                if not was_playing:
                    self.root.after(100, self.audio_player.pause)
                    self.root.after(100, self.video_engine.pause)
                else:
                    self.root.after(50, self.start_opencv_playback)

            elif effect == "none" and self.mode != "vlc":
                position_to_restore = self.video_engine.get_elapsed_time()
                playback_status = self.video_engine.playing

                self.video_engine.stop()
                self.audio_player.stop()

                if self.video_label is not None:
                    self.video_label.pack_forget()

                self.mode = "vlc"
                media = self.instance.media_new(self.current_file)
                self.player.set_media(media)
                self.player.play()

                def set_vlc_position():
                    if self.player.is_playing() or self.player.get_length() > 0:
                        if self.player.get_length() > 0:
                            self.player.set_time(int(position_to_restore))
                            print(f"Posicionando em: {self.format_time(position_to_restore)}")
                            self.scale_var.set(int(position_to_restore))
                            total_time = self.player.get_length()
                            self.time_label.config(text=f"{self.format_time(position_to_restore)} / {self.format_time(total_time)}")
                            if not playback_status:
                                self.root.after(50, self.player.pause)
                            self.player.audio_set_volume(self.volume_var.get())
                            return
                    self.root.after(100, set_vlc_position)

                self.root.after(200, set_vlc_position)
            elif effect != "none" and self.mode == "opencv":
                self.video_engine.reload_frame_buffer()
                if not self.video_engine.playing and self.video_label is not None:
                    frame = self.video_engine.get_current_frame()
                    if frame is not None:
                        if len(frame.shape) == 2:
                            img = Image.fromarray(frame).convert('RGB')
                        else:
                            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        photo = ImageTk.PhotoImage(image=img)
                        self.video_label.config(image=photo)
                        self.video_label.image = photo

    def on_close(self):
        """Método chamado ao fechar a aplicação"""
        if hasattr(self, "exporter"):
            self.exporter.cancel_all_exports()

        if hasattr(self, "exporter") and self.exporter.export_thread and self.exporter.export_thread.is_alive():
            self.exporter.export_thread.join(timeout=1.0)

        if self.mode == "opencv":
            self.video_engine.stop()

        self.player.stop()
        self.audio_player.stop()
        self.root.destroy()

    def check_ffmpeg_availability(self):
        """Verifica se o FFmpeg está disponível no sistema"""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            return result.returncode == 0
        except:
            return False
