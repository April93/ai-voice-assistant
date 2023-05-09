# ai-voice-assistant

I hooked up you.com's youchat into speech to text and text to speech services, to create an AI voice assistant. I'm using this alongside vb-cable and vmagicmirror to create an anime character chatbot. The code supports both text and voice input, configuring voice, wake word, and prompt context, and of course vb-cable support. See '-h' for launch parameters.


## Optional setup

### Local language model with Oobabooga Web UI

You can use this with [Oobabooga's Web UI](https://github.com/oobabooga/text-generation-webui/) for a local LLM (instead of Youchat) by launching with `--ooba`. When using this, you can also load in TavernAI png/webp or Pygmalion/Oobabooga json character cards with `--chara filename.png`. The script assumes you are running oobabooga with `--extensions api` and on port 5000 (default).

### Local speech recognition with Vosk

Use `--vosk` to run with local vosk speech recognition instead of the default google one. Make sure you download a model from [here](https://alphacephei.com/vosk/models) and put it in the folder with it named as `model`. Make sure to run with `--voiceinput` when using speech to text input.

### Moegoe TTS

A modified version of moegoe is included in the repo. To use it, place a compatible `.pth` and `.json` model in `mymoegoe/models/` ensuring both the pth and json have the same name, then launch the script with `--moegoe`. The script assumes a model named `g.pth` and `g.json`. You can manually select it by launching with `--mgmodel modelnamehere` for example: `--mgmodel g` without file extensions. If the voice is too fast or too slow, you can modify the speed with `--voicespeed 1.0` adjusting the number (higher is slower). A popular model with thousands of anime voices can be found [here.](https://huggingface.co/spaces/skytnt/moe-tts/tree/main/saved_model/15)

### Anime character visualization with VMagicMirror and VB-Cable

For windows and mac it's possible to install [VB-Cable](https://vb-audio.com/Cable/) and [VMagicMirror](https://github.com/malaybaku/VMagicMirror/) to send the TTS output to an on screen anime character. Launch the script with `--vbcable` to send TTS to vbcable. Then run VMagicMirror and set the microphone to the virtual VB-Cable microphone.

## Launch Arguments

| Launch Argument  | Description |
| ------------- |:-------------:|
|`--vbcable`|Send audio to vb-cable virtual microphone.|
|`--voiceinput`|Interact with the AI using your voice instead of text.|
|`--pc='string'`|set a prompt context. To prepend to prompts. Optionally can be set as fake history.|
|`--pcaschat`|Sets prompt context to be a fake chat history.|
|`--caphistory=number`|Caps chat history length. Default is 4. Set to -1 to disable.|
|`--voice=number`|Set the TTS voice.|
|`--voices`|List voices on your computer.|
|`--wakeword='string'`|Sets the wake word when using voice input.|
|`--alwayslisten`|Always listen for input, not using a wake word.|
|`--ooba`|Use local oobabooga webui as LLM instead of YouChat.|
|`--vosk`|Use local vosk as STT instead of Google.|
|`--chara='filename'`|Load tavernai character card or oobabooga character json file.|
|`--moegoe`|Use moegoe as TTS instead of default TTS.|
|`--bootmsg='string'`|What to say when booting up.|
|`--wakeprompt`|Like alwayslisten, but doesn't prompt unless wakeword is included.|
|`--nowakeping`|Doesn't ping when starting to listen for wake word|
|`--voicespeed=number`|Speed of moegoe tts. Higher=slower. default is 1.|
|`--mgmodel='filename'`|set the filename of the moegoe model. default is g|
|`-v`|Print debug info.|