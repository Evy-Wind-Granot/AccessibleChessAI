#imports
import pygame as p
import random 
from multiprocessing import Process, Queue
import pyttsx3

# Constants
BOARD_WIDTH = BOARD_HEIGHT = 512 #size pf the chess board itself
MOVE_LOG_PANEL_WIDTH = 230 # width of the move log panel
MOVE_LOG_PANEL_HEIGHT = BOARD_HEIGHT # height of the move log panel, same as the board height so its leveled
DIMENSION = 8 #board length and width the number of squares in each row and column
SQ_SIZE = BOARD_HEIGHT // DIMENSION #the size of each square
MAX_FPS = 15 #frame rates
IMAGES = {} #Holding for the images


#START OF ENGINE
#---------------------------------------------------------------------------------------------------------------------------------
# Class definition for GameState
class GameState():
    def __init__(self):
        # Board setup and other initialization
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]]
        self.moveFunctions = {'p': self.getPawnMoves, 'R': self.getRookMoves, 'N':self.getKnightMoves, 'B':self.getBishopMoves, 'Q':self.getQueenMoves, 'K':self.getKingMoves}

        self.whiteToMove = True #True if it's white's turn to move, Flase if it is black's turn to move
        self.moveLog = [] #An array of all the moves
        #Saving the location of the kings to make looking for checks, checkmates and stalemates easier
        self.whiteKingLocation = (7,4) 
        self.blackKingLocation = (0,4)
        self.checkMate = False #True if the game is in checkmate
        self.staleMate = False #True if the game is in stalemate
        self.enpassantPossible = () #coordiantes for the square where an en passant capture is possible
        self.enpassantPossibleLog = [self.enpassantPossible] #Saves the coordinates of the last possible enpassant move mainly for undoing moves
        self.currentCastlingRight = CastleRights(True, True, True, True) #Checks if the kings can castling on king and/or queens side
        self.castleRigthsLog = [CastleRights(self.currentCastlingRight.wks, self.currentCastlingRight.bks, self.currentCastlingRight.wqs,self.currentCastlingRight.bqs)]

    #takes a mve and excetutes it (will not work for castling, pawn promotion, and enpassant)
    def makeMove(self, move):
        self.board[move.startRow][move.startCol] = "--"
        self.board[move.endRow][move.endCol] = move.pieceMoved
        self.moveLog.append(move)#log the move so we can undo it later
        self.whiteToMove = not self.whiteToMove
        #updated the kings locaiton
        if move.pieceMoved == "wK":
            self.whiteKingLocation = (move.endRow, move.endCol)
        elif move.pieceMoved == "bK":
            self.blackKingLocation = (move.endRow, move.endCol)

        #pawn promotion
        if move.isPawnPromotion:
            self.board[move.endRow][move.endCol] = move.pieceMoved[0] + 'Q'

        #En passant move
        if move.isEnpassantMove:
            self.board[move.startRow][move.endCol] = '--'#capture the pawn
        
        #update enpassantpossible variable
        if move.pieceMoved[1] == 'p' and abs(move.startRow-move.endRow) == 2: #only on 2 square pawn advances
            self.enpassantPossible = ((move.startRow + move.endRow)//2, move.startCol)
        else:
            self.enpassantPossible = ()

        #castle move
        if move.isCastleMove:
            if move.endCol - move.startCol == 2: #kingside castle move
                self.board[move.endRow][move.endCol-1] = self.board[move.endRow][move.endCol+1]#moves rook
                self.board[move.endRow][move.endCol+1] = '--'
            else:#queen castle side
                self.board[move.endRow][move.endCol+1] = self.board[move.endRow][move.endCol-2]#moves rook
                self.board[move.endRow][move.endCol-2] = '--'#erase the rook

        self.enpassantPossibleLog.append(self.enpassantPossible)

        #update castling rights - whenever king or rook move
        self.updateCastleRights(move)
        self.castleRigthsLog.append(CastleRights(self.currentCastlingRight.wks, self.currentCastlingRight.bks, self.currentCastlingRight.wqs,self.currentCastlingRight.bqs))


    #undo the last move made
    def undoMove(self):
        if len(self.moveLog) != 0:#make sure there is a move to undo
            move = self.moveLog.pop() #move stores the deleted move
            self.board[move.startRow][move.startCol] = move.pieceMoved
            self.board[move.endRow][move.endCol] = move.pieceCaptured #put back captured piece
            self.whiteToMove = not self.whiteToMove#switch turn back
            #update kings position
            if move.pieceMoved == "wK":
                self.whiteKingLocation = (move.startRow, move.startCol)
            elif move.pieceMoved == "bK":
                self.blackKingLocation = (move.startRow, move.startCol)
            
            #undo en passant move
            if move.isEnpassantMove:
                self.board[move.endRow][move.endCol] = '--' #leave landing square blank
                self.board[move.startRow][move.endCol] = move.pieceCaptured #puts the pawn back on the correct square it was captured frok

            self.enpassantPossibleLog.pop()
            self.enpassantPossible = self.enpassantPossibleLog[-1]
            

            #undo castling rights
            self.castleRigthsLog.pop() #get rid of new calstle rights
            newRights = self.castleRigthsLog[-1] #set the current castle rights to the last one in the list
            self.currentCastlingRight = CastleRights(newRights.wks, newRights.bks, newRights.wqs, newRights.bqs)
            #undo castle move
            if move.isCastleMove:
                if move.endCol - move.startCol == 2:#kingside
                    self.board[move.endRow][move.endCol+1] = self.board[move.endRow][move.endCol-1]
                    self.board[move.endRow][move.endCol-1] = '--'
                else:#queenside
                    self.board[move.endRow][move.endCol-2] = self.board[move.endRow][move.endCol+1]
                    self.board[move.endRow][move.endCol+1] = '--'
            #Important incase the previous move was a checkmate or stalemate, makes it so the game can continue when the undo happens
            self.checkMate = False
            self.staleMate = False

    #update the castle rights given the move
    def updateCastleRights(self, move):
        #Checks if the kings or rooks have moved and changes the castling rights accordinly
        if move.pieceMoved == 'wK':
            self.currentCastlingRight.wks = False
            self.currentCastlingRight.wqs = False
        elif move.pieceMoved == 'bK':
            self.currentCastlingRight.bks = False
            self.currentCastlingRight.bqs = False
        elif move.pieceMoved == 'wR':
            if move.startRow == 7:
                if move.startCol == 0:#left rook
                    self.currentCastlingRight.wqs = False
                elif move.startCol == 7:#right rook
                    self.currentCastlingRight.wks = False
        elif move.pieceMoved == 'bR':
            if move.startRow == 0:
                if move.startCol == 0:#left rook
                    self.currentCastlingRight.bqs = False
                elif move.startCol == 7:#right rook
                    self.currentCastlingRight.bks = False

        #if a rook is captured
        if move.pieceCaptured == 'wR':
            if move.endRow == 7:
                if move.endCol == 0:
                    self.currentCastlingRight.wqs = False
                elif move.endCol == 7:
                    self.currentCastlingRight.wks = False
        elif move.pieceCaptured == 'bR':
            if move.endRow == 0:
                if move.endCol == 0:
                    self.currentCastlingRight.bqs = False
                elif move.endCol == 7:
                    self.currentCastlingRight.bks = False


    #all moves considering checks
    def getValidMoves(self):
        tempEnpassantPossible = self.enpassantPossible
        tempCastlingRights = CastleRights(self.currentCastlingRight.wks, self.currentCastlingRight.bks, self.currentCastlingRight.wqs,self.currentCastlingRight.bqs)
        #1 generate all possible moves
        moves = self.getAllPossibleMoves()
        if self.whiteToMove:
            self.getCastleMoves(self.whiteKingLocation[0], self.whiteKingLocation[1], moves)
        else:
            self.getCastleMoves(self.blackKingLocation[0], self.blackKingLocation[1], moves)
        #2 for each move make move
        for i in range(len(moves)-1, -1, -1):# when removing from list start at back
            self.makeMove(moves[i])
            #3 generate all oppenents moves
            #4 for each of your opponents mvoes see if they attack your king
            self.whiteToMove = not self.whiteToMove
            if self.inCheck():
                moves.remove(moves[i]) #5 if they do attack your king, not a valid move
            self.whiteToMove = not self.whiteToMove
            self.undoMove()

        #If the number of valid moves is 0 then the game is in either checkmate or stalemate
        if len(moves) == 0:
            if self.inCheck():
                self.checkMate = True
            else:
                self.staleMate = True

        self.enpassantPossible = tempEnpassantPossible
        self.currentCastlingRight = tempCastlingRights
       
        return moves

    #determine if the current player is in check
    def inCheck(self):
        if self.whiteToMove:
            return self.squareUnderAttack(self.whiteKingLocation[0], self.whiteKingLocation[1])
        else:
            return self.squareUnderAttack(self.blackKingLocation[0], self.blackKingLocation[1])
    
    #determine if the enemy can attack the square r,c
    def squareUnderAttack(self, r, c):
        self.whiteToMove = not self.whiteToMove
        oppMoves = self.getAllPossibleMoves()
        self.whiteToMove = not self.whiteToMove#switch turns back
        for move in oppMoves:
            if move.endRow == r and move.endCol == c:#square under attack!
                return True
        return False

    #gets all the possible moves by the piece without considering if the king is in check or not
    def getAllPossibleMoves(self):
        moves = []
        for r in range(len(self.board)): #number of rows
            for c in range(len(self.board[r])): #number of cols in given row
                turn = self.board[r][c][0]
                if (turn == 'w' and self.whiteToMove) or (turn == 'b' and not self.whiteToMove):
                    piece = self.board[r][c][1]
                    self.moveFunctions[piece](r, c, moves)
        return moves
    

    #Get all pawn moves for the pawn at the specfic square on the board
    def getPawnMoves(self, r, c, moves):
        if self.whiteToMove:# white pawns moves
            if self.board[r-1][c] == "--":#1square pawn advance
                moves.append(Move((r, c) , (r-1,c), self.board))
                if r == 6  and self.board[r-2][c] == "--":
                    moves.append(Move((r, c) , (r-2,c), self.board))
            if c - 1 >= 0: #captures to the left
                if self.board[r-1][c-1][0] == 'b':#enemy to capture
                    moves.append(Move((r, c) , (r-1,c-1), self.board))
                elif (r-1, c-1) == self.enpassantPossible:
                    moves.append(Move((r, c) , (r-1,c-1), self.board, isEnpassantMove=True))
            if c + 1 <= 7:
                if self.board[r-1][c+1][0] == 'b':#enemy to capture
                    moves.append(Move((r, c) , (r-1,c+1), self.board))
                elif (r-1, c+1) == self.enpassantPossible:
                    moves.append(Move((r, c) , (r-1,c+1), self.board, isEnpassantMove=True))
        else:# black pawns moves
            if self.board[r+1][c] == "--":#1square pawn advance
                moves.append(Move((r, c) , (r+1,c), self.board))
                if r == 1  and self.board[r+2][c] == "--":
                    moves.append(Move((r, c) , (r+2,c), self.board))
            if c - 1 >= 0: #captures to the left
                if self.board[r+1][c-1][0] == 'w':#enemy to capture
                    moves.append(Move((r, c) , (r+1,c-1), self.board))
                elif (r+1, c-1) == self.enpassantPossible:
                    moves.append(Move((r, c) , (r+1,c-1), self.board, isEnpassantMove=True))
            if c + 1 <= 7:#capture right
                if self.board[r+1][c+1][0] == 'w':#enemy to capture
                    moves.append(Move((r, c) , (r+1,c+1), self.board))
                elif (r+1, c+1) == self.enpassantPossible:
                    moves.append(Move((r, c) , (r+1,c+1), self.board, isEnpassantMove=True))


    #Get all rook moves for the rook at the specfic square on the board
    def getRookMoves(self, r, c, moves):
        directions = ((-1,0),(0,-1),(1,0),(0,1))#up, left, down, right
        enemyColor = "b" if self.whiteToMove else "w"
        for d in directions:
            for i in range(1,8):
                endRow = r + d[0] * i
                endCol = c + d[1] * i
                if 0 <= endRow < 8 and 0 <= endCol < 8: #on board
                    endPiece = self.board[endRow][endCol]
                    if endPiece == "--":#endpy space valid
                        moves.append(Move((r, c) , (endRow, endCol), self.board))
                    elif (endPiece[0] == enemyColor):#enemy piece valid
                        moves.append(Move((r, c) , (endRow, endCol), self.board))
                        break
                    else:
                        break
                else:#off board
                    break


    #Get all Knight moves for the Knight at the specfic square on the board
    def getKnightMoves(self, r, c, moves):
        knightMoves = ((-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1))#up, left, down, right
        allyColor = "w" if self.whiteToMove else "b"
        for m in knightMoves:
            endRow = r + m[0] 
            endCol = c + m[1]
            if 0 <= endRow < 8 and 0 <= endCol < 8: #on board
                endPiece = self.board[endRow][endCol]
                if endPiece[0] != allyColor:#not an ally piece (empty or enemy)
                    moves.append(Move((r, c) , (endRow,endCol), self.board))


    #Get all Bishop moves for the Bishop at the specfic square on the board
    def getBishopMoves(self, r, c, moves):
        directions = ((-1,-1),(1,-1),(1,1),(-1,1))#up, left, down, right
        enemyColor = "b" if self.whiteToMove else "w"
        for d in directions:
            for i in range(1,8):
                endRow = r + d[0] * i
                endCol = c + d[1] * i
                if 0 <= endRow < 8 and 0 <= endCol < 8: #on board
                    endPiece = self.board[endRow][endCol]
                    if endPiece == "--":#endpy space valid
                        moves.append(Move((r, c) , (endRow,endCol), self.board))
                    elif (endPiece[0] == enemyColor):#enemy piece valid
                        moves.append(Move((r, c) , (endRow,endCol), self.board))
                        break
                    else:
                        break
                else:
                    break


    #Get all Queen moves for the Queen at the specfic square on the board
    def getQueenMoves(self, r, c, moves):
        #Queen is really just a bishop and a rook mashed together so this is a simple sortcut
        self.getRookMoves(r,c,moves)
        self.getBishopMoves(r,c,moves)


    #Get all king moves for the king at the specfic square on the board
    def getKingMoves(self, r, c, moves):
        kingMoves = [(1, 0), (1, 1), (1, -1), (-1, 0), (-1, 1), (-1, -1), (0, 1), (0, -1)]
        allyColor = "w" if self.whiteToMove else "b"
        for i in range(8):
            endRow = r + kingMoves[i][0] 
            endCol = c + kingMoves[i][1] 
            if 0 <= endRow < 8 and 0 <= endCol < 8: #on board
                endPiece = self.board[endRow][endCol]
                if endPiece[0] != allyColor:
                    moves.append(Move((r, c) , (endRow,endCol), self.board))
        

    #generate all valid castle movs for the king at (r,c ) and add them to the list of moves
    def getCastleMoves(self, r, c, moves):
        if self.squareUnderAttack(r, c):
            return#cant castle white we are in check
        if (self.whiteToMove and self.currentCastlingRight.wks) or (not self.whiteToMove and self.currentCastlingRight.bks):
            self.getKingsideCastleMoves(r, c, moves)
        if (self.whiteToMove and self.currentCastlingRight.wqs) or (not self.whiteToMove and self.currentCastlingRight.bqs):
            self.getQueensideCastleMoves(r, c, moves)
        
    #makes sure the squares between the king and the rook on the king side are empty and not under attack by an enemy piece
    def getKingsideCastleMoves(self, r, c, moves):
        if self.board[r][c+1] == '--' and self.board[r][c+2] == '--':
            if not self.squareUnderAttack(r, c + 1) and not self.squareUnderAttack(r, c + 2):
                moves.append(Move((r,c), (r,c+2), self.board, isCastleMove =True))

    #makes sure the squares between the king and the rook on the queens side are empty and not under attack by an enemy piece
    def getQueensideCastleMoves(self, r, c, moves):
        if self.board[r][c-1] == '--' and self.board[r][c-2] == '--' and self.board[r][c-3] == '--':
            if not self.squareUnderAttack(r, c - 1) and not self.squareUnderAttack(r, c - 2):
                moves.append(Move((r,c), (r,c-2), self.board, isCastleMove =True))



class CastleRights():
    def __init__(self, wks, bks, wqs, bqs):
        self.wks = wks
        self.bks = bks
        self.wqs = wqs
        self.bqs = bqs


class Move():
    #map keys to values
    # key : value
    ranksToRows = {"1": 7, "2": 6, "3": 5, "4": 4, "5":3, "6":2, "7":1, "8":0}
    rowsToRanks = {v: k for k, v in ranksToRows.items()}#reverses the dictionary
    filesToCols = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h":7}
    colsToFiles = {v: k for k, v in filesToCols.items()}

    def __init__(self, startSq, endSq, board, isEnpassantMove=False, isCastleMove=False):
        self.startRow = startSq[0] #the piece's starting square row wise 1,2,3....8
        self.startCol = startSq[1] #the piece's starting square column wise a,b,c...h
        self.endRow = endSq[0] #the piece's ending square row wise 1,2,3....8
        self.endCol = endSq[1] #the piece's ending square column wise a,b,c...h
        self.pieceMoved = board[self.startRow][self.startCol] #Gets the piece moved
        self.pieceCaptured = board[self.endRow][self.endCol]#Gets the piece captured
        #pawn promotion stuffs
        self.isPawnPromotion = (self.pieceMoved == 'wp' and self.endRow == 0) or (self.pieceMoved == 'bp' and self.endRow == 7)
        #en passant stuffs
        self.isEnpassantMove = isEnpassantMove
        if self.isEnpassantMove:
            self.pieceCaptured = 'wp' if self.pieceMoved == 'bp' else 'bp'

        self.isCapture= self.pieceCaptured != '--'
        #castle move
        self.isCastleMove = isCastleMove
        #make a unique move id
        self.moveID = self.startRow * 1000 + self.startCol * 100 + self.endRow * 10 + self.endCol

    #overriding the equals method
    def __eq__(self, other):
        if isinstance(other, Move):
            return self.moveID == other.moveID
        return False

    def getChessNotation(self):
        #you can add to make this real chess notation
        return self.getRankFile(self.startRow, self.startCol) + self.getRankFile(self.endRow,  self.endCol)
    
    #helper function for the string and the chess notation
    def getRankFile(self, r, c):
        return self.colsToFiles[c] + self.rowsToRanks[r]
    
    #overriding the string function
    def __str__(self):
        #castle move
        if self.isCastleMove:
            return "O-O" if self.endCol == 6 else "O-O-O"
        
        endSquare = self.getRankFile(self.endRow, self.endCol)
        #pawn moves
        if self.pieceMoved[1] == 'p':
            if self.isCapture:
                return self.colsToFiles[self.startCol] + "X" + endSquare
            else:
                return endSquare
        
        moveString = self.pieceMoved[1]
        #add an x if a piece is captured
        if self.isCapture:
            moveString += 'x'
        return moveString + endSquare 
    
#END OF ENGINE

#-------------------------------------------------------------------------------------------------------------------
#start of bulding the AI

#Give each piece a score of importance, queen is more important that pawn, lower importance == lower value
pieceScores = {"K": 900, "Q": 90, "R": 50, "B": 30, "N":30, "p":10}

#score the value for a knight on each square on the board, white or black
knightScores = [
    [-5.0, -4.0, -3.0, -3.0, -3.0, -3.0, -4.0, -5.0],
    [-4.0, -2.0,  0.0,  0.0,  0.0,  0.0, -2.0, -4.0],
    [-3.0,  0.0,  0.5,  1.5,  1.5,  0.5,  0.0, -3.0],
    [-3.0,  0.5,  1.5,  2.0,  2.0,  1.5,  0.5, -3.0],
    [-3.0,  0.0,  1.5,  2.0,  2.0,  1.5,  0.0, -3.0],
    [-3.0,  0.5,  1.0,  1.5,  1.5,  1.0,  0.5, -3.0],
    [-4.0, -2.0,  0.0,  0.0,  0.0,  0.0, -2.0, -4.0],
    [-5.0, -4.0, -3.0, -3.0, -3.0, -3.0, -4.0, -5.0]
]

#score the value for a white bishop on each square on the board
whiteBishopScores = [
    [ -2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0],
    [ -1.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -1.0],
    [ -1.0,  0.0,  0.5,  1.0,  1.0,  0.5,  0.0, -1.0],
    [ -1.0,  0.5,  0.5,  1.0,  1.0,  0.5,  0.5, -1.0],
    [ -1.0,  0.0,  1.0,  1.0,  1.0,  1.0,  0.0, -1.0],
    [ -1.0,  1.0,  1.0,  1.0,  1.0,  1.0,  1.0, -1.0],
    [ -1.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.5, -1.0],
    [ -2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0]
]

#score the value for a black bishop on each square on the board
blackBishopScores = [
    [ -2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0],
    [ -1.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -1.0],
    [ -1.0,  1.0,  1.0,  1.0,  1.0,  1.0,  1.0, -1.0],
    [ -1.0,  0.0,  1.0,  1.0,  1.0,  1.0,  0.0, -1.0],
    [ -1.0,  0.5,  0.5,  1.0,  1.0,  0.5,  0.5, -1.0],
    [ -1.0,  0.0,  0.5,  1.0,  1.0,  0.5,  0.0, -1.0],
    [ -1.0,  0.5,  0.0,  0.0,  0.0,  0.0,  0.5, -1.0],
    [ -2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0]
]

#score the value for a queen on each square on the board, white or black
queenScores = [
    [ -2.0, -1.0, -1.0, -0.5, -0.5, -1.0, -1.0, -2.0],
    [ -1.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -1.0],
    [ -1.0,  0.0,  0.5,  0.5,  0.5,  0.5,  0.0, -1.0],
    [ -0.5,  0.0,  0.5,  0.5,  0.5,  0.5,  0.0, -0.5],
    [  0.0,  0.0,  0.5,  0.5,  0.5,  0.5,  0.0, -0.5],
    [ -1.0,  0.5,  0.5,  0.5,  0.5,  0.5,  0.0, -1.0],
    [ -1.0,  0.0,  0.5,  0.0,  0.0,  0.0,  0.0, -1.0],
    [ -2.0, -1.0, -1.0, -0.5, -0.5, -1.0, -1.0, -2.0]
]

#score the value for a white rook on each square on the board
whiteRookScores = [
    [  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    [  0.5,  1.0,  1.0,  1.0,  1.0,  1.0,  1.0,  0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [ -0.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [  0.0,  0.0,  0.5,  0.5,  0.5,  0.0,  0.0,  0.0]
]

#score the value for a black rook on each square on the board
blackRookScores = [ 
    [0.0,  0.0,  0.5,  0.5,  0.5,  0.0,  0.0,  0.0],
    [-0.5, 0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [-0.5, 0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [-0.5, 0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [-0.5, 0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [-0.5, 0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -0.5],
    [0.5,  1.0,  1.0,  1.0,  1.0,  1.0,  1.0,  0.5],
    [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0]
]

#score the value for a white pawn on each square on the board
whitePawnScores = [
    [5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0],
    [5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0],
    [1.0,  1.0,  2.0,  3.0,  3.0,  2.0,  1.0,  1.0],
    [0.5,  0.5,  1.0,  2.5,  2.5,  1.0,  0.5,  0.5],
    [0.0,  0.0,  0.0,  2.0,  2.0,  0.0,  0.0,  0.0],
    [0.0, -0.5, -1.0,  0.0,  0.0, -1.0, -0.5,  0.0],
    [0.5,  1.0,  1.0, -2.0, -2.0,  1.0,  1.0,  0.5],
    [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0]
]

#score the value for a black pawn on each square on the board
blackPawnScores = [
    [0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0],
    [0.5,  1.0,  1.0, -2.0, -2.0,  1.0,  1.0,  0.5],
    [0.0, -0.5, -1.0,  0.0,  0.0, -1.0, -0.5,  0.0],
    [0.0,  0.0,  0.0,  2.0,  2.0,  0.0,  0.0,  0.0],
    [0.5,  0.5,  1.0,  2.5,  2.5,  1.0,  0.5,  0.5],
    [1.0,  1.0,  2.0,  3.0,  3.0,  2.0,  1.0,  1.0],
    [5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0],
    [5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0]
]

#score the value for a white king on each square on the board
whiteKingScores = [
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -2.0, -3.0, -3.0, -4.0, -4.0, -3.0, -3.0, -2.0],
    [ -1.0, -2.0, -2.0, -2.0, -2.0, -2.0, -2.0, -1.0],
    [  2.0,  2.0,  0.0,  0.0,  0.0,  0.0,  2.0,  2.0 ],
    [  2.0,  3.0,  1.0,  0.0,  0.0,  1.0,  3.0,  2.0 ]
]

#score the value for a black king on each square on the board
blackKingScores = [
    [  2.0,  3.0,  1.0,  0.0,  0.0,  1.0,  3.0,  2.0 ],
    [  2.0,  2.0,  0.0,  0.0,  0.0,  0.0,  2.0,  2.0 ],
    [ -1.0, -2.0, -2.0, -2.0, -2.0, -2.0, -2.0, -1.0],
    [ -2.0, -3.0, -3.0, -4.0, -4.0, -3.0, -3.0, -2.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
    [ -3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0]
]

#dictionary for the piece scores tables
piecePositionScores = {"wK": whiteKingScores, "bK":blackKingScores, "N":knightScores,  "Q": queenScores, "wB": whiteBishopScores, "bB": blackBishopScores, "wR": whiteRookScores, "bR":blackRookScores, "bp":blackPawnScores, "wp":whitePawnScores}

CHECKMATE = 10000 #value of a checkmate since it wins the game, so make it very valuable
STALEMATE = 0 #value of a stalemate, make it 0, so that it can be reached but might not be the best move
DEPTH = 2 # number of moves ahead the AI will look, can handle, 4-5 max, the greater the number the longer it takes for a move to happen

#picks a random Move and returns it
def findRandomMove(validMoves):
    return validMoves[random.randint(0, len(validMoves) -1)]

#finds the best move based on material alone
def findBestMoveMinMaxNoRecursion(gs, validMoves):
    turnMultiplier =  1 if gs.whiteToMove else -1
    opponentMinMaxScore = CHECKMATE
    bestPlayerMove = None
    random.shuffle(validMoves)
    for playerMove in validMoves:
        gs.makeMove(playerMove)
        opponentsMoves = gs.getValidMoves()
        if gs.staleMate:
            opponentMaxScore = STALEMATE
        elif gs.checkMate:
            opponentMaxScore = -CHECKMATE
        else:
            opponentMaxScore = -CHECKMATE
            for opponentsMoves in opponentsMoves:
                gs.makeMove(opponentsMoves)
                gs.getValidMove()
                if gs.checkMate:
                    score = CHECKMATE
                elif gs.staleMate:
                    score = STALEMATE
                else:
                    score = -turnMultiplier*scoreMaterial(gs.board)
                if (score > opponentMaxScore):
                    opponentMaxScore = score
                    #bestPlayerMove = playerMove
                gs.undoMove()
        if opponentMaxScore  < opponentMinMaxScore:
            opponentMinMaxScore = opponentMaxScore
            bestPlayerMove = playerMove
        gs.undoMove()
    return bestPlayerMove

#helper method to make first recursive call
def findBestMove(gs, validMoves, returnQueue):
    global nextMove
    nextMove = None
    random.shuffle(validMoves)#shuffle moves to make the Nega Max Alpha Beta algorithm stronger
    #findMoveMinMax(gs, validMoves, DEPTH, gs.whiteToMove)
    findMoveNegaMaxAlphaBeta(gs, validMoves, DEPTH, -CHECKMATE, CHECKMATE, 1 if gs.whiteToMove else -1)
    returnQueue.put(nextMove) #multiprocessing

#helper function
def findMoveMinMax(gs, validMoves, depth, whiteToMove):
    global nextMove
    if depth == 0:
        return scoreMaterial(gs.board)

    if whiteToMove:
        maxScore = -CHECKMATE
        for move in validMoves:
            gs.makeMove(move)
            nextMoves = gs.getValidMoves()
            score = findMoveMinMax(gs,nextMoves, depth-1,  False)
            if score > maxScore:
                maxScore = score
                if depth == DEPTH:
                    nextMove = move
            gs.undoMove()
        return maxScore
    else:
        minScore = CHECKMATE
        for move in validMoves:
            gs.makeMove(move)
            nextMoves = gs.getValidMoves()
            score = findMoveMinMax(gs, nextMoves, depth-1, True)
            if score < minScore:
                minScore = score
                if depth == DEPTH:
                    nextMove = move
            gs.undoMove()
        return minScore

#helper function
def findMoveNegaMax(gs, validMoves, depth, turnMulitplier):
    global nextMove
    if depth == 0:
        return turnMulitplier * scoreBoard(gs)
    maxScore = -CHECKMATE
    for move in validMoves:
        gs.makeMove(move)
        nextMoves = gs.getValidMoves()
        score = -findMoveNegaMax(gs, nextMoves, depth-1, -turnMulitplier)
        if score > maxScore:
            maxScore = score
            if depth == DEPTH:
                nextMove = move
        gs.undoMove()
    return maxScore

#Implements the NegaMaxAlphaBeta algorithm to find the best move by pruning poor moves
def findMoveNegaMaxAlphaBeta(gs, validMoves, depth, alpha, beta, turnMulitplier):
    global nextMove
    if depth == 0:
        return turnMulitplier * scoreBoard(gs)
    
    #move ordering - implement later
    maxScore = -CHECKMATE
    for move in validMoves:
        gs.makeMove(move)
        nextMoves = gs.getValidMoves()
        score = -findMoveNegaMaxAlphaBeta(gs, nextMoves, depth-1, -beta, -alpha, -turnMulitplier)
        if score > maxScore:
            maxScore = score
            if depth == DEPTH:
                nextMove = move
        gs.undoMove()
        if maxScore > alpha: #pruning happens
            alpha = maxScore
        if alpha >= beta:
            break
    return maxScore

#positive score is good for white, negative score is good for white
def scoreBoard(gs):
    if gs.checkMate:
        if gs.whiteToMove:
            return -CHECKMATE #black wins
        else:
            return CHECKMATE #white wins  
    elif gs.staleMate:
        return STALEMATE

    score = 0
    for row in range(len(gs.board)):
        for col in range(len(gs.board[row])):
            square = gs.board[row][col]
            if square != "--":
                #score it positionally
                piecePositionScore = 0
                if square[1] == "p" or square[1] == "R" or square[1] == "K" or square[1] == "B":
                    piecePositionScore = piecePositionScores[square][row][col]
                else: #for other pieces
                    piecePositionScore = piecePositionScores[square[1]][row][col]
                #add the positional score to the value of the piece to find the score of the move
                if square[0] == 'w':
                    score += pieceScores[square[1]] + piecePositionScore
                elif square[0] == 'b':
                    score -= pieceScores[square[1]] + piecePositionScore
    return score

#score board based on Material
def scoreMaterial(board):
    score = 0
    for row in board:
        for square in row:
            if square[0] == 'w':
                score += pieceScores[square[1]]
            elif square[0] == 'b':
                score -= pieceScores[square[1]]
    return score
#End of Build AI
#-------------------------------------------------------------------------------------------------------------------

#Start of main 
#initialize images
def loadImages():
    pieces = ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR", "bp", "wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR", "wp"]
    for piece in pieces:
        IMAGES[piece] = p.transform.scale(p.image.load("images/" + piece + ".png"), (SQ_SIZE, SQ_SIZE))

#talker is initializing for pyttsx3, so that we can annouce the move 
talker =  pyttsx3.init()
def main():

    p.init()#initialize pygame
    screen = p.display.set_mode((BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH, BOARD_HEIGHT)) #make the window for the UI
    clock = p.time.Clock()
    screen.fill(p.Color("white"))
    moveLogFont = p.font.SysFont("Arial", 14, False, False)#the font for the moveLog
    gs = GameState()#simplify for calling the gamestate class
    validMoves = gs.getValidMoves()
    moveMade = False #flag variable for when a move is made
    animate = False #flag variable for when we should animate a move
    loadImages()
    running = True
    sqSelected = ()#no square selected initially, keeps track of te last click of the userc(tuple(row, col))
    playerClicks = [] #keeps track of player clicks (two tuples: [(6,4),(4,4)]))
    gameOver = False
    playerOne = False #if a human is playing = true, if AI is playing then false
    playerTwo = False# same logic as above
    AIThinking = False #true when Ai is trying to come up with a move
    audio = True#flag for if you want audio or not, true is want audio
    moveFinderProcess = None
    moveUndone = False
    #main game loop
    while running:
        humanTurn = (gs.whiteToMove and playerOne) or (not gs.whiteToMove and playerTwo)
        for e in p.event.get():
            if e.type == p.QUIT:
                running = False
            #mouse handler
            elif e.type == p.MOUSEBUTTONDOWN:
                if not gameOver:
                    location = p.mouse.get_pos()#(x,y) location of mouse
                    col = location[0] // SQ_SIZE
                    row = location[1] // SQ_SIZE
                    if sqSelected == (row, col) or col >= 8:#the user clicked the same square twice or user clicked mouse log
                        sqSelected = ()
                        playerClicks =[]
                    else:
                        sqSelected = (row, col)
                        playerClicks.append(sqSelected)#append for both 1st and 2nd clicks
                    if len(playerClicks) == 2 and humanTurn:#after 2nd click
                        move = Move(playerClicks[0], playerClicks[1], gs.board)
                        #print(move.getChessNotation())
                        for i in range(len(validMoves)):
                            if move == validMoves[i]:
                                gs.makeMove(validMoves[i])
                                moveMade = True
                                animate = True
                                sqSelected = ()#reset
                                playerClicks = []
                        if not moveMade:
                            playerClicks = [sqSelected]
            #key handler
            elif e.type == p.KEYDOWN:#undo when z is pressed
                if e.key == p.K_z:
                    gs.undoMove()
                    moveMade = True
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True
                if e.key == p.K_r:#reset the board when r is pressed
                    gs = GameState()
                    validMoves = gs.getValidMoves
                    sqSelected = ()
                    playerClicks = []
                    moveMade = False
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True

        #AI move finder logic
        if not gameOver and not humanTurn and not moveUndone:
            if not AIThinking:
                AIThinking = True
                returnQueue = Queue()#used to pass data between threads
                moveFinderProcess = Process(target=findBestMove, args=(gs, validMoves, returnQueue))
                moveFinderProcess.start()# cal findBestMove

            if not moveFinderProcess.is_alive():
                AIMove = returnQueue.get()
                if AIMove is None:
                    AIMove = findRandomMove(validMoves)
                gs.makeMove(AIMove)
                moveMade = True
                animate = True
                AIThinking = False
        
        if moveMade:
            if animate:
                animateMove(gs, gs.moveLog[-1], screen, gs.board, clock)
            validMoves = gs.getValidMoves()
            if audio:
                #speak the last move out loud using talker
                talker.say(gs.moveLog[-1])
                talker.runAndWait()
                talker.stop()
            moveMade = False
            animate = False
            moveUndone = False

        drawGameState(screen, gs, validMoves, sqSelected, moveLogFont)

        if gs.checkMate or gs.staleMate:
            gameOver = True
            drawEndGameText(screen, 'Stalemate' if gs.staleMate else 'Black wins by checkmate' if gs.whiteToMove else 'White wins by checkmate')
        elif not moveMade and (gs.inCheck()):#will highlight the kings current square in red while its in check
            kingRow, kingCol = gs.whiteKingLocation if gs.whiteToMove else gs.blackKingLocation
            s = p.Surface((SQ_SIZE, SQ_SIZE))
            s.set_alpha(100)
            s.fill(p.Color('red'))
            screen.blit(s, (kingCol * SQ_SIZE, kingRow * SQ_SIZE))

        clock.tick(MAX_FPS)
        p.display.flip()

#responsible for all the graphics within a current game state 
def drawGameState(screen, gs , validMoves, sqSelected, moveLogFont):
    drawBoard(screen)
    hightlightSquare(screen, gs, validMoves, sqSelected)
    drawPieces(screen, gs.board)
    drawMoveLog(screen, gs, moveLogFont)

# Draw the squares on the board
def drawBoard(screen):
    global colors
    colors = [p.Color("white"), p.Color("gray")]
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = colors[(r + c) % 2]
            p.draw.rect(screen, color, p.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

#highlight square selected and moves for the piece selected
def hightlightSquare(screen, gs, validMoves, sqSelected):
    if sqSelected != ():
        r, c = sqSelected
        enemyColor = 'b' if gs.board[r][c][0] == 'w' else 'w'
        #kingLocation = gs.whiteKingLocation if enemyColor == 'b' else gs.blackKingLocation
        if gs.board[r][c][0] == ('w' if gs.whiteToMove else 'b'): #make sure that the square selected is a piece tha can be moved
            s = p.Surface((SQ_SIZE,SQ_SIZE))
            s.set_alpha(100) #transparancy value
            s.fill(p.Color('blue'))#highlight the piece that you intent to move in blue
            screen.blit(s,(c*SQ_SIZE,r*SQ_SIZE))

            for move in validMoves:
                if move.startRow == r and move.startCol == c:
                    if gs.board[move.endRow][move.endCol][0] == enemyColor:#check if the ending square is held by enemy
                        s.fill(p.Color('red'))#highlight in red if the piece on the ending square is help by enemy
                    else:
                        s.fill(p.Color('yellow')) #otherwise highlight possible squares in red
                    screen.blit(s, (move.endCol * SQ_SIZE, move.endRow * SQ_SIZE))
                    #break

# Draw the pieces on the board
def drawPieces(screen, board):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                screen.blit(IMAGES[piece], p.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE))

#draws the move log
def drawMoveLog(screen, gs, font):
    moveLogRect = p.Rect(BOARD_WIDTH, 0, MOVE_LOG_PANEL_WIDTH, MOVE_LOG_PANEL_HEIGHT)
    p.draw.rect(screen, p.Color("black"), moveLogRect)
    moveLog = gs.moveLog
    moveTexts = []
    for i in range(0, len(moveLog), 2):
        moveString = str(i//2 + 1) + ". " + str(moveLog[i]) + ", "
        if i + 1 < len(moveLog):#make sure black made a move
            moveString += str(moveLog[i+1])+ " " + " " + " " + " "
        moveTexts.append(moveString)
    movesPerRow = 3
    padding = 5
    lineSpacing = 2
    textY = padding
    for i in range(0, len(moveTexts), movesPerRow):
        text = ""
        for j in range(movesPerRow):
            if i + j < len(moveTexts):
                text += moveTexts[i+j]
        textObject = font.render(text, True, p.Color('white'))
        textLocation = moveLogRect.move(padding, textY)
        screen.blit(textObject,textLocation)
        textY += textObject.get_height() + lineSpacing
        
#animating a move
def animateMove(gs, move, screen, board, clock):
    global colors
    dR = move.endRow - move.startRow
    dC = move.endCol - move.startCol
    framesPerSquare = 7#speed that the piece moves at
    frameCount = (abs(dR) + abs(dC)) * framesPerSquare
    for frame in range(frameCount + 1):
        r, c = ((move.startRow + dR*frame/frameCount), (move.startCol + dC*frame/frameCount))
        drawBoard(screen)
        drawPieces(screen, board)
        #erase the piece moved from its ending square
        color = colors[(move.endRow + move.endCol) % 2]
        endSquare = p.Rect(move.endCol*SQ_SIZE, move.endRow*SQ_SIZE, SQ_SIZE, SQ_SIZE)
        p.draw.rect(screen, color, endSquare)
        #draw captured piece on rectangle
        if move.pieceCaptured != '--':
            if move.isEnpassantMove:
                enPassantRow = (move.endRow + 1) if move.pieceCaptured[0] == 'b' else move.endRow - 1
                endSquare = p.Rect(move.endCol*SQ_SIZE, enPassantRow*SQ_SIZE, SQ_SIZE, SQ_SIZE)
            screen.blit(IMAGES[move.pieceCaptured], endSquare)
        #draw moving piece
        screen.blit(IMAGES[move.pieceMoved], p.Rect(c*SQ_SIZE,r*SQ_SIZE,SQ_SIZE,SQ_SIZE))
        
        p.display.flip()
        clock.tick(60)

def drawEndGameText(screen, text):
    font = p.font.SysFont("Helvitca", 32, True, False)
    textObject = font.render(text, 0, p.Color('Gray'))
    textLocation = p.Rect(0,0, BOARD_WIDTH,BOARD_HEIGHT).move(BOARD_WIDTH/2 - textObject.get_width()/2, BOARD_HEIGHT/2 - textObject.get_height()/2)
    screen.blit(textObject,textLocation)
    textObject = font.render(text, 0, p.Color("Black"))
    screen.blit(textObject, textLocation.move(2,2))


if __name__ == "__main__":
    main()

#end of main

#end of program