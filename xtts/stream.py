import argparse
import json
import subprocess
import sys
import time
from typing import Iterator
from typing import List

import requests

import base64
import io
import os
import tempfile
import wave
import torch
import numpy as np
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts


def save(audio: bytes, filename: str) -> None:
    with open(filename, "wb") as f:
        f.write(audio)


#Model Params
basemodelname = "xtts/models/base v2.0.2/"
modelname = basemodelname
reference = "xtts/voices/en_sample.wav"

config = None
model = None

#Load Model
def loadModel(modelname="base v2.0.2", voice="en_sample"):
    global model, config, reference
    model_path = "xtts/models/"+modelname+"/"
    reference = "xtts/voices/"+voice+".wav"
    configname = model_path+"config.json"
    config = XttsConfig()
    config.load_json(configname)
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir=model_path, eval=True)
    model.cuda()
    print("TTS Model Loaded.")


#clone speaker
def predict_speaker(wav_file):
    """Compute conditioning inputs from reference audio file."""
    gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
        wav_file
    )
    return {
        "gpt_cond_latent": gpt_cond_latent.cpu().squeeze().half().tolist(),
        "speaker_embedding": speaker_embedding.cpu().squeeze().half().tolist(),
    }


#Processing tts wav stuff for stream
def postprocess(wav):
    """Post process the output waveform"""
    if isinstance(wav, list):
        wav = torch.cat(wav, dim=0)
    wav = wav.clone().detach().cpu().numpy()
    wav = wav[None, : int(wav.shape[0])]
    wav = np.clip(wav, -1, 1)
    wav = (wav * 32767).astype(np.int16)
    return wav
def encode_audio_common(frame_input, encode_base64=True, sample_rate=24000, sample_width=2, channels=1):
    """Return base64 encoded audio"""
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, "wb") as vfout:
        vfout.setnchannels(channels)
        vfout.setsampwidth(sample_width)
        vfout.setframerate(sample_rate)
        vfout.writeframes(frame_input)

    wav_buf.seek(0)
    if encode_base64:
        b64_encoded = base64.b64encode(wav_buf.getbuffer()).decode("utf-8")
        return b64_encoded
    else:
        return wav_buf.read()

#Seems to generate the streamed tts output
def predict_streaming_generator(parsed_input: dict):
    speaker_embedding = torch.tensor(parsed_input["speaker_embedding"]).unsqueeze(0).unsqueeze(-1)
    gpt_cond_latent = torch.tensor(parsed_input["gpt_cond_latent"]).reshape((-1, 1024)).unsqueeze(0)
    text = parsed_input["text"]
    language = parsed_input["language"]

    stream_chunk_size = int(parsed_input["stream_chunk_size"])
    add_wav_header = False#parsed_input["add_wav_header"]


    chunks = model.inference_stream(
        text,
        language,
        gpt_cond_latent,
        speaker_embedding,
        stream_chunk_size=stream_chunk_size,
        enable_text_splitting=True
    )

    for i, chunk in enumerate(chunks):
        chunk = postprocess(chunk)
        if i == 0 and add_wav_header:
            #This breaks playaudiostream but works for ffplay?
            yield encode_audio_common(b"", encode_base64=False)
            yield chunk.tobytes()
        else:
            yield chunk.tobytes()

#Plays the tts output live?
def stream_ffplay(audio_stream, output_file=None, save=False):
    if not save:
        ffplay_cmd = ["ffplay", "-nodisp", "-probesize", "1024", "-autoexit", "-"]
    else:
        print("Saving to ", output_file)
        ffplay_cmd = ["ffmpeg", "-probesize", "1024", "-i", "-", output_file]

    ffplay_proc = subprocess.Popen(ffplay_cmd, stdin=subprocess.PIPE)
    for chunk in audio_stream:
        if chunk is not None:
            ffplay_proc.stdin.write(chunk)

    # close on finish
    ffplay_proc.stdin.close()
    ffplay_proc.wait()


def tts(text, speaker, language, stream_chunk_size, verbose=False) -> Iterator[bytes]:
    start = time.perf_counter()
    speaker["text"] = text
    speaker["language"] = language
    speaker["stream_chunk_size"] = stream_chunk_size  # you can reduce it to get faster response, but degrade quality

    
    if verbose:
        end = time.perf_counter()
        print(f"Time to make POST: {end-start}s", file=sys.stderr)

    first = True
    #for chunk in res.iter_content(chunk_size=512):
    for chunk in predict_streaming_generator(speaker):
        if first:
            if verbose:
                end = time.perf_counter()
                print(f"Time to first chunk: {end-start}s", file=sys.stderr)
            first = False
        if chunk:
            yield chunk

    #print("⏱️ response.elapsed:", res.elapsed)


def get_speaker(ref_audio):
    wav_file = open(ref_audio, "rb")
    response = predict_speaker(wav_file)
    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--text",
        default="It took me quite a long time to develop a voice and now that I have it I am not going to be silent.",
        help="text input for TTS"
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language to use default is 'en'  (English)"
    )
    parser.add_argument(
        "--output_file",
        default=None,
        help="Save TTS output to given filename"
    )
    parser.add_argument(
        "--ref_file",
        default=None,
        help="Reference audio file to use, when not given will use default"
    )
    parser.add_argument(
        "--stream_chunk_size",
        default="20",
        help="Stream chunk size , 20 default, reducing will get faster latency but may degrade quality"
    )
    args = parser.parse_args()

    loadModel()

    with open("./default_speaker.json", "r") as file:
        speaker = json.load(file)

    if args.ref_file is not None:
        print("Computing the latents for a new reference...")
        speaker = get_speaker(args.ref_file)

    audio = stream_ffplay(
        tts(
            args.text,
            speaker,
            args.language,
            args.stream_chunk_size
        ), 
        args.output_file,
        save=bool(args.output_file)
    )
    audio = stream_ffplay(
        tts(
            "This should play after the first one.",
            speaker,
            args.language,
            args.stream_chunk_size
        ), 
        args.output_file,
        save=bool(args.output_file)
    )
