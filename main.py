# coding: utf8

import time

WHITE = 0
BLACK = 1


def on_board(pos):
    return pos[0] >= 0 and pos[0] <= 7 and pos[1] >= 0 and pos[1] <= 7


def symbolic_to_tuple(s):
    return ("abcdefgh".index(s[0]), int(s[1]) - 1)


def parse_symbolic_move(s):
    src_sym, dst_sym = s.split(" ")
    return symbolic_to_tuple(src_sym), symbolic_to_tuple(dst_sym)


def tuple_to_symbolic(s):
    return "abcdefgh"[s[0]] + str(s[1] + 1)


class Piece(object):
    def __init__(self, color):
        self.color = color

    def symbol(self):
        return self.symbols[self.color]


class Pawn(Piece):
    symbols = "♙♟"
    value = 1

    def mut(self, src, board):
        x, y = src
        yd = 1 if self.color == WHITE else -1

        # Move by one
        dst = (x, y + yd)
        if dst not in board:
            yield board.move(src, dst)

            # Move by two
            dst = (x, y + yd + yd)
            if dst not in board:
                yield board.move(src, dst)

        # Attack left
        dst = (x - 1, y + yd)
        if x > 0 and dst in board and board[dst].color != self.color:
            yield board.move(src, dst)

        # Attack right
        dst = (x + 1, y + yd)
        if x < 7 and dst in board and board[dst].color != self.color:
            yield board.move(src, dst)

        # FIXME: en passant
        # FIXME: promotion


class Galloper(Piece):
    step_limit = 7

    def mut(self, src, board):
        x, y = src
        for xd, yd in self.directions:
            for i in range(1, self.step_limit + 1):
                dst = (x + xd * i, y + yd * i)
                if not on_board(dst):
                    # We hit a border of board
                    break

                if dst not in board:
                    yield board.move(src, dst)
                else:
                    # We hit a piece
                    if board[dst].color != self.color:
                        # But we can attack it...
                        yield board.move(src, dst)

                    break


class Rook(Galloper):
    symbols = "♖♜"
    value = 5
    directions = (0, 1), (0, -1), (1, 0), (-1, 0)


class Knight(Piece):
    symbols = "♘♞"
    value = 3

    def mut(self, src, board):
        for xd, yd in ((-1, -2), (-1, 2), (1, -2), (1, 2),
                       (-2, -1), (-2, 1), (2, -1), (2, 1)):

            dst = (src[0] + xd, src[1] + yd)
            if not on_board(dst):
                continue

            if dst in board and board[dst].color == self.color:
                continue

            yield board.move(src, dst)


class Bishop(Galloper):
    symbols = "♗♝"
    value = 3
    directions = (-1, -1), (-1, 1), (1, -1), (1, 1)


class Queen(Galloper):
    symbols = "♕♛"
    value = 9
    directions = Rook.directions + Bishop.directions


class King(Galloper):
    symbols = "♔♚"
    value = 1000
    directions = Rook.directions + Bishop.directions
    step_limit = 1

    # FIXME castling


class Board(dict):
    @classmethod
    def initial(self):
        """ Set up starting position. """
        board = Board()
        board.tomove = WHITE

        for x in range(0, 8):
            board[(x, 1)] = Pawn(WHITE)

        board[(0, 0)] = Rook(WHITE)
        board[(1, 0)] = Knight(WHITE)
        board[(2, 0)] = Bishop(WHITE)
        board[(3, 0)] = Queen(WHITE)
        board[(4, 0)] = King(WHITE)
        board[(5, 0)] = Bishop(WHITE)
        board[(6, 0)] = Knight(WHITE)
        board[(7, 0)] = Rook(WHITE)

        blacks = {}
        for (x, y), piece in board.items():
            blacks[(x, 7 - y)] = piece.__class__(BLACK)

        board.update(blacks)
        return board

    def move(self, src, dst):
        """ Clone original board and move piece from src to dst. """

        board = Board()
        board.update(self)
        board[dst] = self[src]
        del board[src]

        board.last_src = src
        board.last_dst = dst
        board.tomove = 1 - self.tomove

        return board

    def __str__(self):
        s = ""
        for y in (7, 6, 5, 4, 3, 2, 1, 0):
            s += str(y + 1)
            s += "|"
            for x in range(0, 8):
                if (x, y) in self:
                    s += self[(x, y)].symbol()
                else:
                    s += " " if (x + y) % 2 else "░"
                s += "|"
            s += "\n"

        s += "  a b c d e f g h"

        return s

    def score(self):
        total = 0

        for piece in self.values():
            value = piece.value if piece.color == WHITE else -piece.value
            total += value

        return total

    def mut(self):
        """ Return all legal boards that can be derived from this one. """

        for src, piece in self.items():
            # Pieces of opposite color don't get to move
            if piece.color != self.tomove:
                continue

            yield from piece.mut(src, self)


class HumanPlayer(object):
    def make_move(self, game):
        board = game[-1]
        if hasattr(board, "last_src"):
            g1 = tuple_to_symbolic(board.last_src)
            g2 = tuple_to_symbolic(board.last_dst)
            print("Opponent moves: %s %s" % (g1, g2))
        print(board)

        success = False
        while not success:

            user_says = input("Your move: ")
            if user_says == "b":
                print("Reverting your last move")
                game.pop()  # opponent's last move
                game.pop()  # our last move
                board = game[-1]
                print(board)
                continue

            success = True
            try:
                src, dst = parse_symbolic_move(user_says)
            except:
                print("Invalid input! Example: 'e4 e5'")
                success = False

        return board.move(src, dst)


class ComputerPlayer(object):

    def __init__(self, side):
        self.side = side

    def make_move(self, board, depth=2):
        best_board, best_score = None, None
        best_board = None

        opponent = ComputerPlayer(1 - self.side)
        for new_board in board.mut():
            needle = new_board
            if depth > 0:
                needle = opponent.make_move(needle, depth - 1)

            score = needle.score()

            if best_score is None:
                best_board, best_score = new_board, score

            if self.side == BLACK and score < best_score:
                best_board, best_score = new_board, score

            if self.side == WHITE and score > best_score:
                best_board, best_score = new_board, score

        return best_board

p1 = HumanPlayer()
p2 = ComputerPlayer(BLACK)
game = [Board.initial()]
while True:
    game.append(p1.make_move(game))
    game.append(p2.make_move(game[-1]))
