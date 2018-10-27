import requests
from bs4 import BeautifulSoup
import os

links = [
	"http://www.pokemondungeon.com/media-downloads/official-artwork/pokemon-sun-and-moon?thumb_limitstart=0#gallery-4904",
	"http://www.pokemondungeon.com/media-downloads/official-artwork/pokemon-sun-and-moon?thumb_limitstart=50#gallery-4904",
	"http://www.pokemondungeon.com/media-downloads/official-artwork/pokemon-sun-and-moon?thumb_limitstart=100#gallery-4904"
]

for page in links:
	r = requests.get(page)
	data = r.text
	soup = BeautifulSoup(data)

	lastIndex = 0

	counter = 0
	for link in soup.find_all('img', {"class": "ig_thumb"}):
		image = link.get("src")
		image = 'http://www.pokemondungeon.com' + image
		image = image.replace('120-120', '800-600')
		image = image.replace('150-150', '800-600')
		image_name = link.get("alt")[0:3]
		if image_name.startswith('0'):
			image_name = image_name[1:]
		print(image_name)
		r2 = requests.get(image)

		sufix = ''
		if os.path.isfile('scrapped/'+image_name+'.png'):
			if lastIndex == int(image_name):
				counter += 1
				sufix = '_' + str(counter)
			else:
				counter = 0
		lastIndex = int(image_name)

		with open('scrapped/'+image_name+sufix+'.png', "wb") as f:
			f.write(r2.content)
		