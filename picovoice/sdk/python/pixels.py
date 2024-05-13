import apa102
import time
import threading
try:
    import queue as Queue
except ImportError:
    import queue as Queue

class Pixels:
    PIXELS_N = 12

    def __init__(self):
        self.colors = [0] * 3 * self.PIXELS_N
        self.dev = apa102.APA102(num_led=self.PIXELS_N)
        self.next = threading.Event()
        self.queue = Queue.Queue()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def wakeup(self):
        self.next.set()
        self.queue.put(self._wakeup)

    def listen(self):
        self.next.set()
        self.queue.put(self._listen)

    def think(self):
        self.next.set()
        self.queue.put(self._think)

    def speak(self):
        self.next.set()
        self.queue.put(self._speak)

    def off(self):
        self.next.set()
        self.queue.put(self._off)

    def _run(self):
        while True:
            func = self.queue.get()
            func()

    def _wakeup(self):
        colors = [0, 0, 255] 
        self.write(colors)

    def _listen(self):
        colors = [0, 255, 0]  
        self.write(colors)

    def _think(self):
        colors = [255, 165, 0]  
        self.write(colors)

    def _speak(self):
        colors = [255, 0, 0]  
        self.write(colors)

    def _off(self):
        self.write([0] * 3 * self.PIXELS_N)

    def write(self, colors):
        for i in range(self.PIXELS_N):
            self.dev.set_pixel(i, int(colors[0]), int(colors[1]), int(colors[2]))

        self.dev.show()

pixels = Pixels()

if __name__ == '__main__':
    try:
        while True:
            pixels.wakeup()
            time.sleep(3)
            pixels.listen()
            time.sleep(3)
            pixels.think()
            time.sleep(3)
            pixels.speak()
            time.sleep(3)
            pixels.off()
            time.sleep(3)
    except KeyboardInterrupt:
        pass
    finally:
        pixels.off()
        time.sleep(1)
