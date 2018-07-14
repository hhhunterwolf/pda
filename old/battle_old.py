import math
import numpy as np
import random

def calculateMatrixResult(possomMatrix):
	outcome = random.random()
	print('Outcome: ' + str(outcome))
	distance = math.fabs(possomMatrix[0][0] - outcome)

	winA = 0
	winB = 0
	draw = 0
	for i in range(0,9):
		for j in range(0,9):
			if i==j:
				draw = draw + possomMatrix[i][j]
			elif i>j:
				winA = winA + possomMatrix[i][j]
			else:
				winB = winB + possomMatrix[i][j]

	print('Win A:' + str(winA))
	print('Win B:' + str(winB))
	print('')
	return (math.fabs(outcome - winA)<math.fabs(outcome - winB))

def generatePossomMatrix(p1possom, p2possom):
	possomMatrix = np.zeros((9,9))
	print('Possom Matrix:')
	for i in range(0,9):
		for j in range(0,9):
			possomMatrix[i][j] = p1possom[i] * p2possom[j]
			print('%.2f' % possomMatrix[i][j] + '\t', end='')
		print('\n')

	print('\n')
	return possomMatrix

def calculatePossom(strAverage):
	possom = []
	e = 2.7182818284590452353602874713527
	print('Possom:')
	for i in range(0,9):
		temp = ((e ** -strAverage) * (strAverage ** i)) / math.factorial(i)
		print(str(temp) + '\t', end='')
		possom.append(temp)

	print('\n')
	return possom

def battle(pokemon1, pokemon2):
	p1Str = pokemon1 / pokemon2
	p2Str = pokemon2 / pokemon1
	
	p1Possom = calculatePossom(p1Str)
	p2Possom = calculatePossom(p2Str)
	
	possomMatrix = generatePossomMatrix(p1Possom, p2Possom)

	result = calculateMatrixResult(possomMatrix)

	return result

def main():
	pokemon1 = 13860
	pokemon2 = 13800

	wins = 0
	for i in range(1,1000):
		if battle(pokemon1, pokemon2):
			wins = wins + 1
	
	print('Wins: ' + str(wins))
  
if __name__== "__main__":
	main()