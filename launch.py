#Speech recognition library, very important
import speech_recognition as sr
#pyttsx3 is our tts engine
import pyttsx3
#Pygame is used to play the wav audio files that pyttsx3 generates
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
from pygame import mixer, _sdl2 as devices
#These are tools used for interfacing with youchat and other data. json, regex, and cloudflare scraper
import json
import cloudscraper
import re
import random
#terminal arg libs
import sys
import getopt
#--------------------------------------
argsv = sys.argv[1:]
options, args = getopt.getopt(argsv, 'h',["vbcable", "voiceinput", "pc=", "pcaschat", "caphistory=", "voice=", "voices", "wakeword=", "alwayslisten"])

#Config variables
vbcable = False
textinput = True
wakeword = "computer"
promptcontext = ""
promptcontextaschat = True
caphistory = 4
voice = 0
alwayslisten = False
waketext = ""

for opt, arg in options:
	if opt == "-h":
		print("--vbcable: Send audio to vb-cable virtual microphone.")
		print("--voiceinput: Interact with the AI using your voice instead of text.")
		print("--pc='string': set a prompt context. To prepend to prompts. Optionally can be set as fake history.")
		print("--pcaschat: Sets prompt context to be a fake chat history.")
		print("--caphistory=number: Caps chat history length. Default is 4. Set to -1 to disable.")
		print("--voice=number: Set the TTS voice.")
		print("--voices: List voices on your computer.")
		print("--wakeword='string': Sets the wake word when using voice input.")
		print("--alwayslisten: Always listen for input, not using a wake word.")
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
		voice = int(arg)
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

#Here we initialize python's audio output
#It checks to see if we enabled vb-cable to pipe the audio to vmagicmirror
#Be sure to turn on listening to the vb-cable mic if you wish to hear the ai speak, otherwise it's silent
if vbcable:
	mixer.init(devicename = "CABLE Input (VB-Audio Virtual Cable)")
else:
	mixer.init()
#a debug print to check our audio devices
#print("Outputs:", devices.audio.get_audio_device_names()[0])

#Here we initialize the tts with a default boot message
#voices[2].id is to get the voice we want.
engine = pyttsx3.init()
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[voice].id)
engine.save_to_file("Booting Up", "temp.wav")
engine.runAndWait();
mixer.music.load("temp.wav")
mixer.music.play()
#--------------------

#Initialize the cloudflare scraper that we use for youchat requests
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

#Wait for speech detected by google
def getaudiogoogle():
	text = ""
	firstit = True
	while text == "":
		r = sr.Recognizer()
		with sr.Microphone() as source:
			if firstit:
				mixer.music.unload()
				mixer.music.load("ping.mp3")
			r.adjust_for_ambient_noise(source)
			if firstit:
				mixer.music.play()
				firstit = False
			print("Listening for Google!")
			audio = r.listen(source)
		try:
			text = r.recognize_google(audio)
			text = text.lower()
		except:
			print("Failed to recognize")
			text = ""
	return text

#Main function. Two different options: whether we wish to use text input or voice
if textinput:
	while True:
		#get input string
		input_string = input("User: ")
		combinedprompt = promptcontext+input_string
		if promptcontextaschat:
			combinedprompt = input_string
		out = sendq(combinedprompt)
		out = re.sub(r'\[.+?\]\(.+?\)', '', out)
		print("YouBot:", out)
		mixer.music.unload()
		engine.save_to_file(out, "temp.wav")
		engine.runAndWait();
		mixer.music.load("temp.wav")
		mixer.music.play()
else:
	stop_listening = None
	while True:

		#Listen for Wake Word
		waketext = ""
		if stop_listening:
			stop_listening(wait_for_stop=False)
		#start microphone recognition
		r = sr.Recognizer()
		waketext = ""
		def callback(recognizer, audio):
			global waketext
			try:
				waketext = r.recognize_google(audio)
				waketext = waketext.lower()
				print("You said: {}".format(waketext))
			except:
				waketext = ""
				print("Failed to recognize!")	
		
		m = sr.Microphone()
		with m as source:
			r.adjust_for_ambient_noise(source)
		stop_listening = r.listen_in_background(m, callback)

		if alwayslisten == True:
			while waketext == "":
				continue
			textg = waketext
		else:
			while wakeword not in waketext:
				continue
			waketext = ""

		#stop_listening(wait_for_stop=False)
		#----------------------------------------


		#Listen for Prompt
		if alwayslisten == False:
			textg = getaudiogoogle()
		#----------------------

		#Send prompt to youchat and print output
		print("You:", textg)
		combinedprompt = promptcontext+textg
		if promptcontextaschat:
			combinedprompt = textg
		out = sendq(combinedprompt)
		out = re.sub(r'\[.+?\]\(.+?\)', '', out)
		print("YouBot:", out)
		#----------------------

		#TTS Response
		mixer.music.unload()
		engine.save_to_file(out, "temp.wav")
		engine.runAndWait();
		mixer.music.load("temp.wav")
		mixer.music.play()
		while mixer.music.get_busy() == True:
			continue
		mixer.music.unload()
		#-------------------