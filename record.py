from stream import MicrophoneStream
from datetime import datetime
import wave

rate = 16000
chunk = int(rate / 10)  
secondsRecorded = 600    #10 minutes

fragments = []


with MicrophoneStream(rate, chunk) as inStream:
    print("recording")
    sampleWidth = inStream.getSampleWidth()
    for i in range(0, int(rate / chunk * secondsRecorded)):
        fragments.extend(inStream.get())

print("recording ended")

timestamp = datetime.utcnow().timestamp()
recordingName = "recording_" + str(timestamp) + ".wav"

outFile = wave.open(recordingName, 'wb')
outFile.setframerate(rate)
outFile.setnchannels(1)
outFile.setsampwidth(sampleWidth)
outFile.writeframes(b''.join(fragments))
outFile.close()
    
