import os
import cv2
import time
import threading
import shutil
import subprocess
import tempfile
import vlc
import tkinter as tk
from tkinter import ttk

class VideoExporter:
    def __init__(self, video_player):
        """
        Classe responsável por gerenciar a exportação de vídeos com efeitos.
        Recebe uma referência à instância de VideoPlayer para acessar variáveis e a interface.
        """
        self.video_player = video_player
        self.root = video_player.root
        self.export_queue = []
        self.current_export = None
        self.export_thread = None
        self.is_exporting = False

    def queue_video_export(self):
        """Adiciona o vídeo atual à fila de exportação"""
        if not self.video_player.current_file:
            return

        effect = self.video_player.effect_var.get()
        if effect == "none":
            return

        # Verifica/cria a pasta "Videos"
        videos_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Videos")
        if not os.path.exists(videos_dir):
            os.makedirs(videos_dir)

        original_filename = os.path.basename(self.video_player.current_file)
        filename_without_ext, extension = os.path.splitext(original_filename)
        output_filename = f"{effect}_{filename_without_ext}{extension}"
        output_path = os.path.join(videos_dir, output_filename)
        temp_output_path = os.path.join(videos_dir, f"temp_{output_filename}")

        # Evita duplicidade na fila
        for item in self.export_queue:
            if item["output_path"] == output_path:
                return

        export_item = {
            "input_path": self.video_player.current_file,
            "output_path": output_path,
            "temp_output_path": temp_output_path,
            "effect": effect,
            "frame": None,
            "progress_bar": None,
            "cancel_button": None,
            "status_label": None,
            "cancelled": False
        }

        self.export_queue.append(export_item)
        self.add_export_item_to_ui(export_item)

        # Ativa o botão para cancelar todas as exportações
        self.video_player.btn_cancel_all.config(state=tk.NORMAL)

        if not self.is_exporting:
            self.process_next_export()

    def add_export_item_to_ui(self, export_item):
        """Adiciona um item de exportação à interface do usuário"""
        item_frame = tk.Frame(self.video_player.queue_container, bg="#363636", relief=tk.RAISED, bd=1)
        item_frame.pack(fill=tk.X, pady=2)

        filename = os.path.basename(export_item["input_path"])
        effect_name = export_item["effect"]

        info_label = tk.Label(item_frame, text=f"{filename} - Efeito: {effect_name}",
                              bg="#363636", fg="white", anchor="w")
        info_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(5, 0))

        status_label = tk.Label(item_frame, text="Aguardando...",
                                bg="#363636", fg="#AAAAAA", anchor="w")
        status_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0, 2))

        progress_bar = ttk.Progressbar(item_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        cancel_button = tk.Button(item_frame, text="✕", bg="#4A4A4A", fg="white",
                                  relief=tk.FLAT, command=lambda: self.cancel_export(export_item))
        cancel_button.pack(side=tk.RIGHT, padx=5, pady=5)

        export_item["frame"] = item_frame
        export_item["progress_bar"] = progress_bar
        export_item["cancel_button"] = cancel_button
        export_item["status_label"] = status_label

    def process_next_export(self):
        """Processa o próximo item na fila de exportação"""
        if len(self.export_queue) == 0:
            self.is_exporting = False
            self.video_player.btn_cancel_all.config(state=tk.DISABLED)
            return

        self.is_exporting = True
        self.current_export = self.export_queue[0]
        self.current_export["status_label"].config(text="Processando...")

        self.export_thread = threading.Thread(target=self.export_video_with_effect, daemon=True)
        self.export_thread.start()

    def export_video_with_effect(self):
        """Processa o vídeo com efeito em uma thread separada"""
        export_item = self.current_export

        try:
            input_path = export_item["input_path"]
            output_path = export_item["output_path"]
            temp_output_path = export_item["temp_output_path"]
            effect = export_item["effect"]

            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                self.update_export_status(export_item, "Erro: Não foi possível abrir o vídeo", True)
                return

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height), True)

            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if export_item["cancelled"]:
                    cap.release()
                    out.release()
                    if os.path.exists(temp_output_path):
                        os.remove(temp_output_path)
                    self.update_export_status(export_item, "Cancelado", True)
                    return

                processed_frame = self.video_player.effects_processor.apply_effect_to_frame(frame, effect)
                if len(processed_frame.shape) == 2:
                    processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_GRAY2BGR)

                out.write(processed_frame)
                frame_count += 1
                progress = int((frame_count / total_frames) * 75)
                self.root.after(0, lambda p=progress: self.update_export_progress(export_item, p))

                if frame_count % 30 == 0:
                    time.sleep(0.001)

            cap.release()
            out.release()

            self.root.after(0, lambda: self.update_export_status(export_item, "Mesclando áudio..."))

            self.combine_video_with_original_audio(input_path, temp_output_path, output_path, export_item)

            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)

            self.update_export_status(export_item, "Concluído", True)

        except Exception as e:
            error_msg = f"Erro: {str(e)}"
            self.update_export_status(export_item, error_msg, True)
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)
            if os.path.exists(output_path):
                os.remove(output_path)

    def update_export_progress(self, export_item, progress):
        """Atualiza o progresso da exportação na interface"""
        if export_item["progress_bar"]:
            export_item["progress_bar"]["value"] = progress

    def update_export_status(self, export_item, status, finished=False):
        """Atualiza o status da exportação na interface"""
        if export_item["status_label"]:
            export_item["status_label"].config(text=status)

        if finished:
            if export_item in self.export_queue:
                self.export_queue.remove(export_item)

            if status == "Cancelado":
                self.root.after(2000, lambda: self.remove_export_item(export_item))
            elif status == "Concluído":
                export_item["status_label"].config(fg="#00FF00")
                self.root.after(5000, lambda: self.remove_export_item(export_item))
            else:
                export_item["status_label"].config(fg="#FF0000")

            self.current_export = None
            self.process_next_export()

    def remove_export_item(self, export_item):
        """Remove o item de exportação da interface"""
        if export_item["frame"]:
            export_item["frame"].destroy()

    def cancel_export(self, export_item):
        """Cancela a exportação de um item específico"""
        if export_item == self.current_export:
            export_item["cancelled"] = True
            export_item["status_label"].config(text="Cancelando...")
        else:
            if export_item in self.export_queue:
                self.export_queue.remove(export_item)
                self.remove_export_item(export_item)

        if len(self.export_queue) == 0:
            self.video_player.btn_cancel_all.config(state=tk.DISABLED)

    def cancel_all_exports(self):
        """Cancela todas as exportações pendentes"""
        if self.current_export:
            self.current_export["cancelled"] = True
            self.current_export["status_label"].config(text="Cancelando...")

        for item in self.export_queue[:]:
            if item != self.current_export:
                self.export_queue.remove(item)
                self.remove_export_item(item)

        self.video_player.btn_cancel_all.config(state=tk.DISABLED)

    def combine_video_with_original_audio(self, original_video, processed_video, output_path, export_item):
        """
        Combina o vídeo processado com o áudio do vídeo original usando FFmpeg.
        Em caso de falha, tenta um método alternativo.
        """
        try:
            cmd = [
                "ffmpeg",
                "-i", processed_video,
                "-i", original_video,
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                output_path,
                "-y"
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.try_alternative_audio_muxing(original_video, processed_video, output_path, export_item)
            else:
                self.root.after(0, lambda: self.update_export_progress(export_item, 100))
        except Exception as e:
            self.try_alternative_audio_muxing(original_video, processed_video, output_path, export_item)

    def try_alternative_audio_muxing(self, original_video, processed_video, output_path, export_item):
        """
        Método alternativo para extrair áudio e mesclar com o vídeo usando métodos disponíveis.
        """
        try:
            audio_temp = tempfile.mktemp(suffix=".wav")
            instance = vlc.Instance()
            player = instance.media_player_new()
            media = instance.media_new(original_video)
            media.add_option(f":sout=#transcode{{acodec=wav,channels=2,samplerate=44100}}:file{{dst={audio_temp}}}")
            media.add_option(":no-sout-video")
            player.set_media(media)
            player.play()

            while player.get_state() != vlc.State.Ended:
                if export_item["cancelled"]:
                    player.stop()
                    if os.path.exists(audio_temp):
                        os.remove(audio_temp)
                    return
                time.sleep(0.5)

            self.root.after(0, lambda: self.update_export_progress(export_item, 90))
            shutil.copy2(processed_video, output_path)
            self.root.after(0, lambda: self.update_export_status(export_item,
                "Concluído (sem áudio - FFmpeg não encontrado)"))

            if os.path.exists(audio_temp):
                os.remove(audio_temp)

        except Exception as e:
            shutil.copy2(processed_video, output_path)
            self.root.after(0, lambda: self.update_export_status(export_item,
                "Concluído (sem áudio - falha ao processar)"))
