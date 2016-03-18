# coding: utf8

WHITE = 1
BLACK = -1


def on_board(pos):
    return pos[0] >= 0 and pos[0] <= 7 and pos[1] >= 0 and pos[1] <= 7


def symbolic_to_tuple(s):
    return ("abcdefgh".index(s[0]), int(s[1]) - 1)


def parse_symbolic_move(s):
    src_sym, dst_sym = s.split(" ")
    return symbolic_to_tuple(src_sym), symbolic_to_tuple(dst_sym)


def tuple_to_symbolic(s):
    return "abcdefgh"[s[0]] + str(s[1] + 1)


class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    @classmethod
    def red(cls, s):
        return cls.RED + s + cls.END


class Piece(object):
    def __init__(self, color):
        self.color = color
        self.symbol = self.symbols[0] if color == WHITE else self.symbols[1]
        self.value = self.base_value * color


class Pawn(Piece):
    symbols = "♙♟"
    base_value = 1

    def mut(self, src, board):
        x, y = src
        yd = self.color

        # Move by one
        dst = (x, y + yd)
        if dst not in board:
            yield board.move(src, dst)

            # If on starting row, allow a move by two
            if self.color == WHITE and y == 1:
                dst = (x, 3)
                if dst not in board:
                    yield board.move(src, dst)
            elif self.color == BLACK and y == 6:
                dst = (x, 4)
                if dst not in board:
                    yield board.move(src, dst)

        # Capture left
        dst = (x - 1, y + yd)
        if x > 0 and dst in board and board[dst].color != self.color:
            yield board.move(src, dst)

        # Capture right
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
                        # But we can capture it...
                        yield board.move(src, dst)

                    break


class Rook(Galloper):
    symbols = "♖♜"
    base_value = 5
    directions = (0, 1), (0, -1), (1, 0), (-1, 0)


class Knight(Piece):
    symbols = "♘♞"
    base_value = 3

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
    base_value = 3
    directions = (-1, -1), (-1, 1), (1, -1), (1, 1)


class Queen(Galloper):
    symbols = "♕♛"
    base_value = 9
    directions = Rook.directions + Bishop.directions


class King(Galloper):
    symbols = "♔♚"
    base_value = 1000
    directions = Rook.directions + Bishop.directions
    step_limit = 1

    # FIXME castling


class Board(dict):
    @classmethod
    def initial(self):
        """ Set up starting position. """
        board = Board()
        board.last_src = (-1, -1)
        board.last_dst = (-1, -1)
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

        board.last_src, board.last_dst = src, dst
        board.tomove = -self.tomove  # toggles WHITE/BLACK

        return board

    def __str__(self):
        s = ""
        for y in (7, 6, 5, 4, 3, 2, 1, 0):
            s += str(y + 1)
            s += "|"
            for x in range(0, 8):
                if (x, y) in self:
                    symbol = self[(x, y)].symbol
                    if self.last_dst == (x, y):
                        symbol = Color.red(symbol)
                    s += symbol
                else:
                    s += " " if (x + y) % 2 else "░"
                s += "|"
            s += "\n"

        s += "  a b c d e f g h"

        return s

    def score(self):
        """ Calculate score for current board and current player.

        score = 0: both players have equal chances
        score > 0: player to move has an advantage
        score > 100: player to move has already won (enemy king is dead)
        score < 0: opponent has an advantage
        score < -100: player to move has lost

        """

        value_sum = sum(piece.value for piece in self.values())
        return value_sum * self.tomove

    def mut(self):
        """ Return all legal boards that can be derived from this one. """

        for src, piece in self.items():
            # Pieces of opposite color don't get to move
            if piece.color != self.tomove:
                continue

            yield from piece.mut(src, self)

    def move_is_legal(self, src, dst):
        for new_board in self.mut():
            if new_board.last_src == src and new_board.last_dst == dst:
                return True

        return False

    def is_lost(self):
        return self.score() < -100

    def is_won(self):
        return self.score() > 100


class HumanPlayer(object):
    def make_move(self, game):
        board = game[-1]
        if board.last_src != (-1, -1):
            g1 = tuple_to_symbolic(board.last_src)
            g2 = tuple_to_symbolic(board.last_dst)
            print("Opponent moves: %s %s" % (g1, g2))
        print(board)

        move_seems_valid = False
        while not move_seems_valid:
            user_says = input("Your move ('b' to undo): ")
            if user_says == "b":
                print("Reverting your last move")
                game.pop()  # opponent's last move
                game.pop()  # our last move
                board = game[-1]
                print(board)
                continue

            move_seems_valid = True
            try:
                src, dst = parse_symbolic_move(user_says)
                if not board.move_is_legal(src, dst):
                    print("Illegal move!")
                    move_seems_valid = False
            except:
                print("Invalid input! Example: 'e4 e5'")
                move_seems_valid = False

        new_board = board.move(src, dst)
        print(new_board)
        return new_board


class ComputerPlayer(object):
    def make_move(self, board, depth=3):
        best_board, best_score = None, None

        for new_board in board.mut():
            if new_board.is_lost():
                # Opponent's king is killed, pick this move
                return new_board
            elif new_board.is_won():
                # Our king is killed, this move is a no-go
                continue

            needle = new_board
            if depth > 0:
                needle = self.make_move(needle, depth - 1)

            score = needle.score()

            if best_score is None or score > best_score:
                best_board, best_score = new_board, score

        return best_board

human = HumanPlayer()
computer = ComputerPlayer()
game = [Board.initial()]
while True:
    game.append(human.make_move(game))
    game.append(computer.make_move(game[-1]))
