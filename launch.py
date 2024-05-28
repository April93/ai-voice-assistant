#Speech recognition library, very important
import speech_recognition as sr
#Alternative speech recognition with whisper
from whisper_mic.whisper_mic import WhisperMic
#pyttsx3 is our tts engine
import pyttsx3
#Load other TTS
import mymoegoe.tts as mytts
import xtts.tts as xtts
import xtts.stream as xttsstream
#Pygame is used to play the wav audio files that pyttsx3 generates
# import os
# os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
# from pygame import mixer, _sdl2 as devices
#These are tools used for interfacing with youchat and other data. json, regex, and cloudflare scraper
import json
import cloudscraper
import re
import random
import threading
#Ooba Reqs
import requests
#LM Studio and Other OpenAI compatibles Reqs
import openai
#Character Card Reqs
from PIL import Image
from PIL.ExifTags import TAGS
import base64
#terminal arg libs
import sys
import getopt
import time
#Needed for piping to vbcable and playing TTS
import sounddevice as sd
import soundfile as sf
import numpy as np
import os
#--------------------------------------
argsv = sys.argv[1:]
options, args = getopt.getopt(argsv, 'hv',
	["vbcable", "voiceinput", "pc=", "pcaschat", "caphistory=", "voice=", "voices", "wakeword=", 
	"alwayslisten", "ooba", "openai", "vosk", "googlestt", "chara=", "moegoe", "xtts", "bootmsg=", "wakeprompt", "nowakeping", 'voicespeed=', 'mgmodel=', 'template='])

#Config variables
vbcable = False
textinput = True
wakeword = "computer"
promptcontext = ""
promptcontextaschat = False
caphistory = 4
voice = None
alwayslisten = False
waketext = ""
ooba = False
openaiapi = False
vosk = False
googlestt = False
ttsengine = "pyttsx3"
wakeprompt = False
wakeping = True
charafilename = ""
speed = 1 
bootmsg = "Booting Up"
mgmodel = "g"
xttsmodel = "base v2.0.2"
verbose = False
chatml = False
phi3 = False
streamchunks = 20

# Put your URI end point:port here for your openai inference server (such as LM Studio) 
openai.api_base='http://localhost:1234/v1'
# Put in an empty API Key for LM stuido
openai.api_key=''
openaimodel = "local model"

script_path = os.path.abspath(__file__)
directory = os.path.dirname(script_path)

for opt, arg in options:
	if opt == "-h":
		print("--vbcable: Send audio to vb-cable virtual microphone.")
		print("--voiceinput: Interact with the AI using your voice instead of text.")
		print("--pc='string': set a prompt context. To prepend to prompts. Optionally can be set as fake history.")
		print("--pcaschat: Sets prompt context to be a fake chat history.")
		print("--caphistory=number: Caps chat history length. Default is 4. Set to -1 to disable.")
		print("--voice=number/string: Set the TTS voice.")
		print("--voices: List voices on your computer.")
		print("--wakeword='string': Sets the wake word when using voice input.")
		print("--alwayslisten: Always listen for input, not using a wake word.")
		print("--ooba: Use local oobabooga webui as LLM instead of YouChat.")
		print("--openai: Use openai api as LLM instead of YouChat.")
		print("--vosk: Use local vosk as STT.")
		print("--googlestt: Use google's online service as STT.")
		print("--chara='filename': Load tavernai character card or oobabooga character json file.")
		print("--moegoe: Use moegoe as TTS instead of default TTS.")
		print("--xtts: Use xtts as TTS instead of default TTS.")
		print("--bootmsg='string': What to say when booting up.")
		print("--wakeprompt: Like alwayslisten, but doesn't prompt unless wakeword is included.")
		print("--nowakeping: Doesn't ping when starting to listen for wake word")
		print("--voicespeed=number: Speed of moegoe tts. Higher=slower. default is 1.")
		print("--mgmodel='filename': set the filename of the moegoe model. default is g")
		print("--template='string': specify a prompt template (chatml or phi3). default typical chat format.")
		print("-v: Print debug info.")
		sys.exit(2)
	elif opt == '--vbcable':
		vbcable = True
	elif opt == '--voiceinput':
		textinput = False
	elif opt == '--pc':
		promptcontext = "["+arg+"]"
	elif opt == "--pcaschat":
		promptcontextaschat = True
	elif opt == "--caphistory":
		caphistory = int(arg)
	elif opt == '--voice':
		voice = arg
	elif opt == '--voices':
		engine = pyttsx3.init()
		voices = engine.getProperty('voices')
		for v in voices:
			print (v)
		sys.exit(2)
	elif opt == '--wakeword':
		wakeword = arg
	elif opt == '--alwayslisten':
		alwayslisten = True
	elif opt == "--ooba":
		ooba = True
	elif opt == "--openai":
		openaiapi = True
	elif opt == "--vosk":
		vosk = True
	elif opt == "--googlestt":
		googlestt = True
	elif opt == "--chara":
		charafilename = arg
	elif opt == "--moegoe":
		ttsengine = "moegoe"
	elif opt == "--xtts":
		ttsengine = "xtts"
	elif opt == "--bootmsg":
		bootmsg = arg
	elif opt == "--wakeprompt":
		wakeprompt = True
	elif opt == "--nowakeping":
		wakeping = False
	elif opt == "--voicespeed":
		speed = float(arg)
	elif opt == "--mgmodel":
		mgmodel = arg
		xttsmodel = arg
	elif opt == "--template":
		if arg == "chatml":
			chatml = True
		if arg == "phi3":
			phi3 = True
	elif opt == "-v":
		verbose = True


# Find VB-Cable device IDs
vbcable_output = None
vbcable_input = None
if vbcable:
	for device in sd.query_devices():
		if 'CABLE Output' in device['name'] and device['max_input_channels'] == 2 and vbcable_output == None:
			if verbose:
				print("Found Cable Output.", device['name'], device['index'])
			vbcable_output = device["index"]
		if 'CABLE Input' in device['name'] and device['max_output_channels'] == 2 and vbcable_input == None:
			if verbose:
				print("Found Cable Input.", device['name'], device['index'])
			vbcable_input = device["index"]

#New function to load and play the tts outputs. Check for vbcable vs speaker
def playaudio():
	audiofile = os.path.join(directory,"temp.wav")
	if os.path.isfile(audiofile):
		data, fs = sf.read(audiofile, dtype='float32')
		data_stereo = np.tile(data, (2, 1)).T.copy(order='C')
		delay = int(fs * 0.2)  # 100ms delay
		zeros = np.zeros((delay, 2))
		sd.play(zeros, fs, blocking=True, device=sd.default.device)
		sd.play(data, fs, device=sd.default.device)
		if vbcable:
			with sd.OutputStream(device=vbcable_input,
								samplerate=fs,
								channels=2) as stream:
				stream.write(data_stereo)
		sd.wait()
	else:
		print("Generated TTS audio temp.wav not found!")
def playstream(audio_stream, stream1, stream2):
	for chunk in audio_stream:
		#Get chunk data into np format (pcm audio samples)
		audio_pcm = np.frombuffer(chunk, dtype=np.int16)
		# Convert PCM audio samples to 32-bit floating-point values
		#data_float = audio_pcm.astype(np.float32) / 32768.0
		stream1.write(audio_pcm)
		if stream2 != None:
			stream2.write(audio_pcm)

def playaudiostream(audio_stream):
	# xttsstream.stream_ffplay(audio_stream)
	with sd.OutputStream(device=sd.default.device,
								samplerate=24000,
								channels=1, blocksize=44544, latency=1, dtype='int16') as stream1:
		if vbcable:
			with sd.OutputStream(device=vbcable_input,
								samplerate=24000,
								channels=1, blocksize=44544, latency=1, dtype='int16') as stream2:
				playstream(audio_stream, stream1, stream2)
		else:
			playstream(audio_stream, stream1, None)

def playchime(pingpong="ping"):
	data, fs = sf.read(os.path.join(directory,pingpong+".wav"), dtype='float32')
	sd.play(data, fs, device=sd.default.device)

#Here we initialize python's audio output
#It checks to see if we enabled vb-cable to pipe the audio to vmagicmirror
#Be sure to turn on listening to the vb-cable mic if you wish to hear the ai speak, otherwise it's silent
# if vbcable:
# 	mixer.init(devicename = "CABLE Input (VB-Audio Virtual Cable)")
# else:
# 	mixer.init()
#a debug print to check our audio devices
#print("Outputs:", devices.audio.get_audio_device_names()[0])


#Here we initialize the tts with a default boot message
#voices[2].id is to get the voice we want.
if ttsengine == "pyttsx3":
	if voice == None:
		voice = 0
	engine = pyttsx3.init()
	voices = engine.getProperty('voices')
	if len(voices) == 0:
		print("No TTS voices detected. Please install a TTS voice on your OS.")
		sys.exit(2)
	engine.setProperty('voice', voices[int(voice)].id)
	engine.save_to_file(bootmsg, os.path.join(directory,"temp.wav"))
	engine.runAndWait();
	playaudio()
#--------------------

if ttsengine == "moegoe":
	if voice == None:
		voice = 0
	mytts.loadtts(mgmodel)
	mytts.tts(bootmsg, os.path.join(directory,"temp.wav"), voice=int(voice), speed=speed)
	playaudio()

if ttsengine == "xtts":
	if voice == None:
		voice = "en_sample"
	xttsstream.loadModel(xttsmodel, voice=voice)
	speaker = xttsstream.get_speaker(xttsstream.reference)
	audio = playaudiostream(xttsstream.tts(bootmsg, speaker, "en", streamchunks))
	#xtts.loadModel(xttsmodel, voice=voice)
	#xtts.generateSpeech(bootmsg, os.path.join(directory,"temp.wav"))
	#playaudio()

#Load sfx
# ping = mixer.Sound("ping.wav")
# pong = mixer.Sound("pong.wav")

#Initialize the cloudflare scraper that we use for youchat requests
if not ooba and not openaiapi:
	scraper = cloudscraper.create_scraper(ecdhCurve='secp384r1')

#New traceid function. This fetches the needed traceid for youchat to function
def getinitialtraceid():
	headers = {
		'Accept': 'text/event-stream',
		'Connection': 'keep-alive',
		'Sec-Fetch-Mode': 'cors',
		'Sec-Fetch-Site': 'same-origin',
		'Sec-GPC': '1',
		'Referer': 'https://you.com/search?q=hello&fromSearchBar=true&tbm=youchat'
	}
	payload = {'q': "hello"}
	try:
		response = scraper.get("https://you.com/search", params=payload, headers=headers)
	except cloudscraper.exceptions.CloudflareChallengeError as e:
		return "Sorry, there was a cloudflare error. Please try again."

	data = response.text
	match = re.search(r'"initialTraceId":"(.+?)"', data)
	first_capture_group = match.group(1)
	#print("traceid:", first_capture_group)
	return first_capture_group
if not ooba and not openaiapi:
	traceid = getinitialtraceid()
	randuuid = str(random.random())[2:]
#print("Random UUID:", randuuid)
#---------------------------

#sendq is the youchat api request. Just enter prompt for the parameter and we get the response back
#chat variable is kept updated with chat history
chat=[]
def sendq(question):
	global chat, traceid, randuuid
	headers = {
		'Accept': 'text/event-stream',
		'Connection': 'keep-alive',
		'Sec-Fetch-Mode': 'cors',
		'Sec-Fetch-Site': 'same-origin',
		'Sec-GPC': '1',
		'Referer': 'https://you.com/search?q=hello&fromSearchBar=true&tbm=youchat',
		'Cookie': ('uuid_guest='+randuuid+";").encode()
	}
	if promptcontextaschat:
		chat.append({"question":'"'+promptcontext+'"', "answer":''})
	payload = {
		'q': question, 
		'chat': str(chat), 
		'queryTraceId': traceid, 
		'domain': 'youchat',
		'page': '1',
		'count': '10',
		'safeSearch': 'Off',
		'onShoppingPage': 'false',
		'freshness':'Month',
		'mkt':'',
		'responseFilter': 'WebPages,Translations,TimeZone,Computation,RelatedSearches'
		}
	try:
		response = scraper.get("https://you.com/api/streamingSearch", params=payload, headers=headers, stream=True)
	except cloudscraper.exceptions.CloudflareChallengeError as e:
		return "Sorry, there was a cloudflare error. Please try again."

	output = ""
	for line in response.iter_lines():
		if line:
			decoded_line = line.decode("utf-8")
			if decoded_line != "{}":
				key, value = decoded_line.split(":", 1)
				key = key.strip()
				value = value.strip()
				if key == "data":
					if value == "I'm Mr. Meeseeks. Look at me.":
						break
					data = json.loads(value)
					if "youChatToken" in data:
						output += data["youChatToken"]
			else:
				return "Sorry, the AI server is too busy. An error has occurred. Please try again."
	if caphistory >= 0:
		if len(chat) > caphistory:
			chat = chat[:0-caphistory]
	chat.append({"question":'"'+question+'"', "answer":'"'+output+'"'})
	return output

#Initialize Character Persona Details for Ooba LLM
yourname = "You"
charactername = "Friend"
characterpersona = ""
worldscenario = "Reply as the user's friend. Make up details about yourself. Do not mention or say you are an AI. Respond only with one or two sentences and keeps responses brief."
exampledialogue = ""
exampledialogue = re.sub(r'{{char}}', charactername, exampledialogue)
exampledialogue = re.sub(r'{{user}}', yourname, exampledialogue)
greeting = ""

def loadcharacard(filename):
	global charactername, characterpersona, worldscenario, exampledialogue, greeting
	if verbose: 
		print("PNG/WEBP character file loading...")
	# load the image
	img = Image.open(filename)
	exif_data = img._getexif()
	img.load()
	chara = ""
	if filename[-4:] == ".png":
		chara = img.info["chara"]
		decoded_bytes = base64.b64decode(chara)
		decoded_string = decoded_bytes.decode('utf-8')
		chara = decoded_string
	if filename[-4:] == "webp":
		for tag_id, value in exif_data.items():
			tag = TAGS.get(tag_id, tag_id)
			if tag == "UserComment":
				chara = value[8:]

	charajson = json.loads(chara)
	print("Loading "+charajson['name'])
	charactername = charajson['name']
	characterpersona = charajson['description']+"\nPersonality: "+charajson['personality']
	characterpersona = re.sub(r'{{char}}', charactername, characterpersona)
	characterpersona = re.sub(r'{{user}}', yourname, characterpersona)
	worldscenario = charajson['scenario']
	worldscenario = re.sub(r'{{char}}', charactername, worldscenario)
	worldscenario = re.sub(r'{{user}}', yourname, worldscenario)
	greeting = charajson['first_mes']
	greeting = re.sub(r'{{char}}', charactername, greeting)
	greeting = re.sub(r'{{user}}', yourname, greeting)
	exampledialogue = charajson['mes_example']
	exampledialogue = re.sub(r'{{char}}', charactername, exampledialogue)
	exampledialogue = re.sub(r'{{user}}', yourname, exampledialogue)

def loadoobacharjson(filename):
	global charactername, characterpersona, worldscenario, exampledialogue, greeting
	if verbose: 
		print("JSON character file loading...")
	with open(filename, encoding="utf-8") as f:
		data = json.load(f)
		print("Loading "+data['char_name'])
		charactername = data['char_name']
		characterpersona = data['char_persona']
		characterpersona = re.sub(r'{{char}}', charactername, characterpersona)
		characterpersona = re.sub(r'{{user}}', yourname, characterpersona)
		worldscenario = data['world_scenario']
		worldscenario = re.sub(r'{{char}}', charactername, worldscenario)
		worldscenario = re.sub(r'{{user}}', yourname, worldscenario)
		greeting = data['char_greeting']
		greeting = re.sub(r'{{char}}', charactername, greeting)
		greeting = re.sub(r'{{user}}', yourname, greeting)
		exampledialogue = data['example_dialogue']
		exampledialogue = re.sub(r'{{char}}', charactername, exampledialogue)
		exampledialogue = re.sub(r'{{user}}', yourname, exampledialogue)

def loadchara(filename):
	if verbose:
		print("Chara file extension:", filename[-4:])
	if filename[-4:] == "json":
		loadoobacharjson(filename)
	elif filename[-4:] == ".png" or filename[-4:] == "webp":
		loadcharacard(filename)
	else:
		print("Could not detect character format...")

if charafilename != "":
	loadchara(charafilename)

if greeting != "":
	print(charactername+": "+greeting)
	chat.append({"question":'', "answer":greeting})
	out = re.sub("\n", "", greeting)
	out = re.sub("[\"\']", "", out)
	out = re.sub("[^\x00-\x7F]+", "", out)
	out = re.sub("[<>]", "", out)
	out = re.sub("-", " - ", out)
	if ttsengine == "pyttsx3":
		engine.save_to_file(out, os.path.join(directory,"temp.wav"))
		engine.runAndWait();
	if ttsengine == "moegoe":
		mytts.tts(out, os.path.join(directory,"temp.wav"), voice=int(voice), speed=speed)
	if ttsengine == "xtts":
		audio = playaudiostream(xttsstream.tts(out, speaker, "en", streamchunks))
		#xtts.generateSpeech(out, os.path.join(directory,"temp.wav"))
	if ttsengine != "xtts":
		playaudio()

#Creates the prompt for non-youchat apis
def createprompt(question):
	global chat, yourname, charactername
	prompt = ""

	#ChatML
	promptuserstart = "<|im_start|>"
	promptend = "<|im_end|>"
	promptassistantstart = "<|im_start|>"

	#Phi 3
	if phi3:
		promptuserstart = "<|user|>"
		promptend = "<|end|>"
		promptassistantstart = "<|assistant|>"

	if chatml:
		prompt = promptuserstart+"system\n"
		yourname = "user"
		charactername = "assistant"
	if phi3:
		prompt = "<|system|>"#promptuserstart+"\n"
	#Handle legacy prompt context
	if promptcontextaschat:
		chat.append({"question":'"'+promptcontext+'"', "answer":''})
	else:
		prompt = promptcontext+"\n"
	
	#characterpersona = "You are chatting with Bot. Bot is an AI assistant that helps answer your questions."

	#Add Character Context
	if characterpersona != "":
		prompt += charactername+"'s Persona: "+characterpersona+"\n"
	if worldscenario != "":
		prompt += "Scenario: "+worldscenario+"\n"
	if exampledialogue != "" and not chatml and not phi3:
		prompt += "<START>"+"\n"+exampledialogue+"\n"
	if (characterpersona != "" or worldscenario != "" or exampledialogue != "") and not chatml and not phi3:
		prompt += "<START>"

	if chatml:
		prompt += promptend+"\n"

	#Add Chat History to Prompt
	for ch in chat:
		if ch["question"] != "":
			if chatml:
				prompt += promptuserstart+yourname+"\n"+ch["question"]+promptend+"\n"
			elif phi3:
				prompt += promptuserstart+"\n"+ch["question"]+promptend+"\n"
			else:
				prompt += '\n'+yourname+': '+ch["question"]
		if ch["answer"] != "":
			if chatml:
				prompt += promptassistantstart+charactername+"\n"+ch["answer"]+promptend+"\n"
			elif phi3:
				prompt += promptassistantstart+"\n"+ch["answer"]+promptend+"\n"
			else:
				prompt += '\n'+charactername+': '+ch["answer"]

	#Add newest chat to prompt
	if chatml:
		prompt += promptuserstart+yourname+"\n"+question+promptend+"\n"+promptassistantstart+charactername+"\n"
	elif phi3:
		prompt += promptuserstart+"\n"+question+promptend+"\n"+promptassistantstart+"\n"
	else:
		prompt += '\n'+yourname+': '
		prompt += question
		prompt += '\n'+charactername+': '
	return prompt

#openaisendq is the openai api request.
def openaisendq(question):
	global chat

	prompt = createprompt(question)

	#Set stopping strings. This tells LLM to stop writing.
	stopping_strings = ["\n"+yourname, "\n"+charactername, "<STOP>", "<END>", "<START>", "<|im_end|>", "<|im_start|>", "<|user|>", "<|end|>", "<|assistant|>"]

	#formatted_prompt = f"{yourname}: {question}\n{charactername}:"
	messages = [{"role": "user", "content": prompt}]
	response = openai.ChatCompletion.create(
		model=openaimodel,
		messages=messages,
		stop=stopping_strings,
		#temperature=0.0
		# temperature=0.7,
		# rep_pen = 1.18,
		# top_p = 1
	)
	output = response.choices[0].message["content"]
	#Append message to chat history
	if caphistory >= 0:
		if len(chat) > caphistory:
			chat = chat[:0-caphistory]
	chat.append({"question":'"'+question+'"', "answer":'"'+output+'"'})
	return output

#oobasendq is the oobabooga api request. Just enter prompt for the parameter and we get the response back
def oobasendq(question):
	global chat

	prompt = createprompt(question)

	#Set stopping strings. This tells LLM to stop writing.
	stopping_strings = ["\n"+yourname, "\n"+charactername]

	#print(prompt)
	#Send the request
	data = {"prompt": prompt, "stopping_strings": stopping_strings, "temperature": 0.7, "rep_pen": 1.18, "top_p":1}
	response = requests.post('http://127.0.0.1:5000/api/v1/generate', data=json.dumps(data))
	if response.status_code == 200:

		#Get the output from the response
		if verbose:
			print(response.content)
		jsondata = json.loads(response.content.decode('utf-8'))
		output = str(jsondata['results'][0]['text']).strip()

		#Append message to chat history
		if caphistory >= 0:
			if len(chat) > caphistory:
				chat = chat[:0-caphistory]
		chat.append({"question":'"'+question+'"', "answer":'"'+output+'"'})

		return output
	else:
		return "Error"


def getaudiovosknew(r, m, wake=False):
	global ping
	print("New Vosk Recognizer")
	text = ""
	firstit = True
	while text == "":
		with m as source:
			r.adjust_for_ambient_noise(source)
			if firstit:
				if (wake and wakeping) or (not wake):
					playchime("ping")
				firstit = False
			print("Listening for Vosk!")
			audio = r.listen(source)
		try:
			text = r.recognize_vosk(audio)
			text = text.lower()
		except:
			print("Failed to recognize")
			text = ""
	output = json.loads(text)["text"]
	print("Detected speech:", output)
	return output

def getaudiogooglenew(r, m, wake=False):
	global ping 
	print("New Google Recognizer")
	text = ""
	firstit = True
	while text == "":
		with m as source:
			r.adjust_for_ambient_noise(source)
			if firstit:
				if (wake and wakeping) or (not wake):
					playchime("ping")
				firstit = False
			print("Listening for Google!")
			audio = r.listen(source)
		try:
			text = r.recognize_google(audio)
			text = text.lower()
		except:
			print("Failed to recognize")
			text = ""
	print("Detected speech:", text)
	return text

#Main function. Two different options: whether we wish to use text input or voice
if textinput:
	while True:
		#get input string
		input_string = input(yourname+": ")
		combinedprompt = promptcontext+input_string
		if promptcontextaschat:
			combinedprompt = input_string
		start_time = time.time()

		#Send prompt to LLM
		if ooba:
			out = oobasendq(input_string)
		elif openaiapi:
			out = openaisendq(input_string)
		else:
			#Youchat
			out = sendq(combinedprompt)
			out = re.sub(r'\[.+?\]\(.+?\)', '', out)

		#Print response
		print(charactername+":", out)
		end_time = time.time()
		elapsed_time = end_time - start_time
		if verbose:
			print("Text-Gen time: ", elapsed_time, "seconds")

		#Clear out string to ensure TTS doesn't crash
		out = re.sub("\n", "", out)
		out = re.sub("[\"\']", "", out)
		out = re.sub("[^\x00-\x7F]+", "", out)
		out = re.sub("[<>]", "", out)
		out = re.sub("-", " ", out)
		if out and out != "":
			# Text to speech to a file
			#tts.tts_to_file(text=out, file_path="temp.wav")
			if ttsengine == "pyttsx3":
				engine.save_to_file(out, os.path.join(directory,"temp.wav"))
				engine.runAndWait();
			elif ttsengine == "moegoe":
				mytts.tts(out, os.path.join(directory,"temp.wav"), voice=int(voice), speed=speed)
			elif ttsengine == "xtts":
				#xtts.generateSpeech(out, os.path.join(directory,"temp.wav"))
				end_time = time.time()
				elapsed_time = end_time - start_time
				if verbose:
					print("Elapsed time: ", elapsed_time, "seconds")
				audio = playaudiostream(xttsstream.tts(out, speaker, "en", streamchunks))
			
			#Calculate and print time if verbose

			if ttsengine != "xtts":
				end_time = time.time()
				elapsed_time = end_time - start_time
				if verbose:
					print("Elapsed time: ", elapsed_time, "seconds")
				threadaudio = threading.Thread(target=playaudio)
				threadaudio.start()
				threadaudio.join()
			#playaudio()
			#mixer.music.load("temp.wav")
			#mixer.music.play()
else:
	stop_listening = None
	#start microphone recognition
	if vosk or googlestt:
		r = sr.Recognizer()
		m = sr.Microphone()
	else:
		mic = WhisperMic(model="base.en")
	# def callback(recognizer, audio):
	# 	global waketext
	# 	#recognizer.adjust_for_ambient_noise(source)
	# 	try:
	# 		if vosk:
	# 			waketext = recognizer.recognize_vosk(audio)
	# 			waketext = json.loads(waketext)["text"]
	# 		else:
	# 			waketext = recognizer.recognize_google(audio)
	# 		waketext = waketext.lower()
	# 		if verbose:
	# 			print("Wake Word Check: {}".format(waketext))
	# 	except:
	# 		waketext = ""
	# 		print("Failed to recognize!")

	if vosk or googlestt:
		with m as source:
			r.adjust_for_ambient_noise(source)
	#stop_listening = r.listen_in_background(m, callback)
	while True:

		#Listen for Wake Word
		# waketext = ""
		# if stop_listening:
		# 	stop_listening(wait_for_stop=False)
		
		waketext = ""
		
		def listenwake():
			global waketext, r, m
			#print(r, m)
			if vosk:
				waketext = getaudiovosknew(r,m, True)
			elif googlestt:
				waketext = getaudiogooglenew(r,m, True)
			else:
				waketext = mic.listen()
				waketext = waketext.lower()
				print("Detected speech:", waketext)
				if wakeping:
					playchime("ping")
		
		if alwayslisten == True:
			while waketext == "":
				listenwake()
				continue
			textg = waketext
			if wakeping:
				playchime("pong")
		else:
			while wakeword not in waketext:
				listenwake()
				continue
			if wakeprompt:
				textg = waketext
			else:
				waketext = ""

		#stop_listening(wait_for_stop=False)
		#----------------------------------------


		#Listen for Prompt
		if alwayslisten == False and wakeprompt == False:
			if vosk:
				textg = getaudiovosknew(r,m)
			elif googlestt:
				textg = getaudiogooglenew(r,m)
			else:
				textg = mic.listen()
			if wakeping:
				playchime("pong")
		#----------------------

		#Send prompt to youchat and print output
		print(yourname+":", textg)
		start_time = time.time()
		combinedprompt = promptcontext+textg
		if promptcontextaschat:
			combinedprompt = textg
		if ooba:
			out = oobasendq(textg)
		elif openaiapi:
			out = openaisendq(textg)
		else:
			#Youchat
			out = sendq(combinedprompt)
			out = re.sub(r'\[.+?\]\(.+?\)', '', out)
		print(charactername+":", out)
		#----------------------

		#TTS Response
		#mixer.music.unload()
		#Clear out string to ensure TTS doesn't crash
		out = re.sub("\n", "", out)
		out = re.sub("\"", "", out)
		out = re.sub("[^\x00-\x7F]+", "", out)
		out = re.sub("[<>]", "", out)
		out = re.sub("-", " ", out)
		if out and out != "":
			if ttsengine == "pyttsx3":
				engine.save_to_file(out, os.path.join(directory,"temp.wav"))
				engine.runAndWait();
			elif ttsengine == "moegoe":
				mytts.tts(out, os.path.join(directory,"temp.wav"), voice=int(voice), speed=speed)
			elif ttsengine == "xtts":
				#xtts.generateSpeech(out, os.path.join(directory,"temp.wav"))
				end_time = time.time()
				elapsed_time = end_time - start_time
				if verbose:
					print("Elapsed time: ", elapsed_time, "seconds")
				audio = playaudiostream(xttsstream.tts(out, speaker, "en", streamchunks))
			
			#Calculate and print time if verbose
			if ttsengine != "xtts":
				end_time = time.time()
				elapsed_time = end_time - start_time
				if verbose:
					print("Elapsed time: ", elapsed_time, "seconds")
				threadaudio = threading.Thread(target=playaudio)
				threadaudio.start()
				threadaudio.join()
			#playaudio()
		#-------------------