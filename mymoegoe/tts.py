#Needed to write wav file, no added install cost
import wave
import struct


#Internal Reqs, no added install cost
from mymoegoe.text import text_to_sequence, _clean_text
from mymoegoe.models import SynthesizerTrn
import mymoegoe.commons as commons

#re is common
import re

#Torch is common
from torch import no_grad, LongTensor

#utils imports. Json and torch both common
from json import loads
from torch import load, FloatTensor
import torch

#Utils
#---------------
class HParams():
  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      if type(v) == dict:
        v = HParams(**v)
      self[k] = v

  def keys(self):
    return self.__dict__.keys()

  def items(self):
    return self.__dict__.items()

  def values(self):
    return self.__dict__.values()

  def __len__(self):
    return len(self.__dict__)

  def __getitem__(self, key):
    return getattr(self, key)

  def __setitem__(self, key, value):
    return setattr(self, key, value)

  def __contains__(self, key):
    return key in self.__dict__

  def __repr__(self):
    return self.__dict__.__repr__()


def load_checkpoint(checkpoint_path, model):
  checkpoint_dict = load(checkpoint_path, map_location="cpu")
  iteration = checkpoint_dict['iteration']
  saved_state_dict = checkpoint_dict['model']
  if hasattr(model, 'module'):
    state_dict = model.module.state_dict()
  else:
    state_dict = model.state_dict()
  new_state_dict= {}
  for k, v in state_dict.items():
    try:
      new_state_dict[k] = saved_state_dict[k]
    except:
      print("Not in dictionary: ", k)
      #logging.info("%s is not in the checkpoint" % k)
      new_state_dict[k] = v
  if hasattr(model, 'module'):
    model.module.load_state_dict(new_state_dict)
  else:
    model.load_state_dict(new_state_dict)
  #logging.info("Loaded checkpoint '{}' (iteration {})" .format(
  #  checkpoint_path, iteration))
  return


def get_hparams_from_file(config_path):
  with open(config_path, "r", encoding="utf-8") as f:
    data = f.read()
  config = loads(data)

  hparams = HParams(**config)
  return hparams



#Script
#---------

#Model Loading
mchoice = "g"
model = "mymoegoe/models/"+mchoice+".pth"
config = "mymoegoe/models/"+mchoice+".json"

#Set speaker/voice, usually 0. Along with wav destination
speaker_id = 0
#out_path = "temp.wav"

#Default Audio Settings
defaultlength = 1
defaultnoisescale = 0.667
defaultnoisedeviation = 0.8

#Audio Settings
length_scale = 1 #length scale
noise_scale = 0.5 #noise scale - phoneme length?
noise_scale_w = 0.1 #deviation of noise - emotionality?

#Input Text
#text = ""

n_symbols = 0
hps_ms = None
net_g_ms = None

def loadtts(mgmodel):
    global model, config, mchoice
    mchoice = mgmodel
    model = "mymoegoe/models/"+mgmodel+".pth"
    config = "mymoegoe/models/"+mgmodel+".json"
    global n_symbols, hps_ms, net_g_ms
    #Load params from the config
    hps_ms = get_hparams_from_file(config)

    #Seems to get number of speakers
    n_speakers = hps_ms.data.n_speakers if 'n_speakers' in hps_ms.data.keys() else 0
    #Seems to get number of symbols?
    n_symbols = len(hps_ms.symbols) if 'symbols' in hps_ms.keys() else 0
    #Get the speakers.
    speakers = hps_ms.speakers if 'speakers' in hps_ms.keys() else ['0']
    #Emotion embedding stuff, seems unneeded
    emotion_embedding = hps_ms.data.emotion_embedding if 'emotion_embedding' in hps_ms.data.keys() else False

    #Some model loading stuff?
    net_g_ms = SynthesizerTrn(
        n_symbols,
        hps_ms.data.filter_length // 2 + 1,
        hps_ms.train.segment_size // hps_ms.data.hop_length,
        n_speakers=n_speakers,
        emotion_embedding=emotion_embedding,
        **hps_ms.model)
    _ = net_g_ms.eval()
    load_checkpoint(model, net_g_ms)

def tts(text, out_path="temp.wav", voice=speaker_id, speed=length_scale):
    speaker_id = voice
    length_scale = speed

    if n_symbols != 0:

        #Clean Text
        #text = text.replace("\"","")
        text_norm = text_to_sequence(text, hps_ms.symbols, hps_ms.data.text_cleaners)
        if hps_ms.data.add_blank:
            text_norm = commons.intersperse(text_norm, 0)
        text_norm = LongTensor(text_norm)
        stn_tst = text_norm
        #---------------


        with no_grad():

            #Generate the TTS audio
            x_tst = stn_tst.unsqueeze(0)
            x_tst_lengths = LongTensor([stn_tst.size(0)])
            sid = LongTensor([speaker_id])
            audio = net_g_ms.infer(x_tst, x_tst_lengths, sid=sid, noise_scale=noise_scale,
                                    noise_scale_w=noise_scale_w, length_scale=length_scale)[0][0, 0].data.cpu().float().numpy()
            

            # Save Wav File
            with wave.open(out_path, 'wb') as wav_file:
                # Set audio file parameters
                wav_file.setnchannels(1)  # Mono audio
                wav_file.setsampwidth(2)  # 16-bit audio
                wav_file.setframerate(hps_ms.data.sampling_rate) # Sample Rate

                # Write audio data to file
                for sample in audio:
                    # Convert sample to 16-bit signed integer format
                    sample = max(-1, min(1, sample))  # Clamp sample to range [-1, 1]
                    sample = int(sample * 32767)  # Scale sample to range [-32767, 32767]
                    packed_sample = struct.pack('<h', sample)  # Convert to little-endian 16-bit signed integer
                    wav_file.writeframes(packed_sample)

#loadtts()
#tts()