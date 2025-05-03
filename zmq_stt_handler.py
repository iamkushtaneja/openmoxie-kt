from .moxie_zmq_handler import ZMQHandler
from .protos.embodied.perception.audio.zmqSTT_pb2 import zmqSTTRequest,zmqSTTResponse
from .deepgram_client import transcribe_audio
import soundfile as sf
import numpy as np
import io
import time
import logging
import concurrent.futures
import asyncio

LOG_WAV=False
DEEPGRAM_MODEL='nova'

logger = logging.getLogger(__name__)

def now_ms():
    return time.time_ns() // 1_000_000


'''
An STT Session is a stream of contiguous audio coming out of the Robot's voice activity detector (VAD). This
is a very simple implementation tuned to OpenAI Whisper.  Their API doesn't support streaming, so we simply
accumulate the audio frames, then transcribe them when complete.
'''
class STTSession:
    def __init__(self, parent, device_id, session_id):
        self._parent = parent
        self._device_id = device_id
        self._session_id = session_id
        self._stream_bytes = bytearray()
        self._start_ts = None
        self._transcription = None

    def on_request(self, req):
        # future ref, this is technically wrong in the design, this ts is realtime on robot, not audio timestamp
        if not self._start_ts:
            self._start_ts = req.timestamp
        self._stream_bytes += req.audio_content
        return len(self._stream_bytes)
    
    async def perform(self):
        logger.info(f'Processing session_id {self._session_id} with {len(self._stream_bytes)} bytes')
        buffer = io.BytesIO()
        sf.write(
            buffer,  # File-like object (None for bytes)
            np.frombuffer(self._stream_bytes, dtype=np.int16),
            16000,
            format='WAV',
            subtype='PCM_16'  # 16-bit PCM
            )
        wav_bytes = buffer.getvalue()
        
        # Create proto response
        resp = zmqSTTResponse()
        resp.uuid = self._session_id
        resp.type = resp.ResponseType.FINAL
        resp.timestamp = now_ms()

        try:
            # Use Deepgram for speech-to-text
            transcript = await transcribe_audio(wav_bytes, model=DEEPGRAM_MODEL, language="en")
            resp.speech = transcript
            resp.start_timestamp = self._start_ts
            resp.end_timestamp = now_ms()
            logger.info(f'STT-FINAL: {transcript}')
        except Exception as e:
            logger.warning(f'Exception handling Deepgram request: {e}')
            resp.error_code = 66
            resp.error_message = str(e)

        # send response to device
        self._parent.zmq_reply(self._device_id, resp)

        if LOG_WAV:
            logfile = f'{self._session_id}.wav'
            with open(logfile, 'wb') as f:
                f.write(wav_bytes)
                logger.info(f'Wrote WAV data to {logfile}')

'''
This is the handler for all Speech data packets.  By default, the Robot uses stt:4, which begins sending
audio data during session to be transcribed.  If Robot is using stt:0, no STT packets will arrive here.
This is also very simple.  We create unique sessions for each device_id / session pair, pass them all the
data inline, and when a session hits end-of-speech, queue transcription to run in the background.
'''
class STTHandler(ZMQHandler):

    def __init__(self, server):
        super().__init__(server)
        self._sessions = {}
        self._worker_queue = concurrent.futures.ThreadPoolExecutor(max_workers=5)

    def handle_zmq(self, device_id, protoname, protodata):
        req = zmqSTTRequest()
        req.ParseFromString(protodata)
        sesskey = ( device_id, req.uuid )
        if sesskey not in self._sessions:
            self._sessions[sesskey] = STTSession(self, sesskey[0], sesskey[1])
        total_sess_bytes = self._sessions[sesskey].on_request(req)
        
        # Process the audio in real-time
        if req.vad == req.VADState.END_OF_SPEECH:
            logger.info(f'Session reached END OF SPEECH')
            sess = self._sessions[sesskey]
            self._worker_queue.submit(lambda: asyncio.run(sess.perform()))
        else:
            # Process partial results if available
            if sesskey in self._sessions:
                sess = self._sessions[sesskey]
                if sess._transcription and sess._transcription.is_partial:
                    self._send_partial_response(device_id, sess._transcription)

    def _send_partial_response(self, device_id, transcription):
        resp = zmqSTTResponse()
        resp.uuid = transcription.session_id
        resp.type = resp.ResponseType.PARTIAL
        resp.timestamp = now_ms()
        resp.speech = transcription.text
        self.zmq_reply(device_id, resp)
