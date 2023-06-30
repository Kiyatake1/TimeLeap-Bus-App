import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
import cv2
import numpy as np

PAGE = """\
<html>
<head>
<title>Streaming da Camera do Raspberry Pi</title>
</head>
<body>
<center><h1>Streaming da Camera do Raspberry Pi</h1></center>
<center><img src="stream.mjpg" width="384" height="288"></center>
</body>
</html>
"""

class StreamingOutput:
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame

                    # Converter o frame em um array numpy
                    frame_array = np.frombuffer(frame, dtype=np.uint8)
                    # Decodificar o array em uma imagem usando o OpenCV
                    img = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

                    # Compressão do frame usando OpenCV
                    _, compressed_frame = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    frame_data = np.array(compressed_frame).tostring()

                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame_data))
                    self.end_headers()
                    self.wfile.write(frame_data)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Falha na conexão: %s', str(e))

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

with picamera.PiCamera(resolution='384x288', framerate=24) as camera:
    output = StreamingOutput()
    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()
    finally:
        camera.stop_recording()
