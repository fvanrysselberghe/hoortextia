class Transcript:
    def __init__(self):
        self.lines = []

    def add(self, item):
        self.lines.append(item)
        return len(self.lines) - 1 
    
    def update(self, key, item):
        if key >= len(self.lines):
            return
        else:
            self.lines[key] = item

class TranscriptCapture:
    def __init__(self, confidence, text):
        self.parts = [TranscriptItem(confidence, text)]
    
    def add(self, capture):
        self.parts.extend(capture.parts)

class TranscriptItem:
    def __init__(self, confidence, text):
        self.confidence = confidence
        self.text = text
        self.offset = 0