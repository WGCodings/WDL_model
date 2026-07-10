import chess
import chess.engine
import json
import time
import random
import zipfile
import io
import urllib.request
from pathlib import Path
import multiprocessing as mp

ENGINE_PATH = "./engines/Pea.exe"
N_GAMES = 1000
BASE_TIME = 8.0
INCREMENT = 0.08
CONCURRENCY = 5
EVAL_CAP = 1500
OUT_DIR = Path("selfplay_data")
OUT_DIR.mkdir(exist_ok=True)

BOOK_ZIP_URL = "https://raw.githubusercontent.com/AndyGrant/openbench-books/master/UHO_Lichess_4852_v1.epd.zip"
BOOK_PATH = OUT_DIR / "UHO_Lichess_4852_v1.epd"

PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}


def download_book():
    if BOOK_PATH.exists():
        return
    print("Downloading opening book...")
    with urllib.request.urlopen(BOOK_ZIP_URL) as resp:
        data = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        epd_name = next(n for n in z.namelist() if n.endswith(".epd"))
        with z.open(epd_name) as src, open(BOOK_PATH, "wb") as dst:
            dst.write(src.read())
    print(f"Book saved to {BOOK_PATH}")


def load_book_fens():
    fens = []
    with open(BOOK_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fields = line.split()
            if len(fields) < 4:
                continue
            board_part = " ".join(fields[:4])
            fen = f"{board_part} 0 1"  # append halfmove/fullmove if missing
            fens.append(fen)
    return fens


def material_count(board: chess.Board) -> int:
    total = 0
    for piece_type, val in PIECE_VALUES.items():
        total += val * len(board.pieces(piece_type, chess.WHITE))
        total += val * len(board.pieces(piece_type, chess.BLACK))
    return total


def play_one_game(engine_path, fens):
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)

    # pick a random valid opening
    board = None
    for _ in range(10):  # retry a few times in case a line is malformed
        fen = random.choice(fens)
        try:
            candidate = chess.Board(fen)
            if candidate.is_valid():
                board = candidate
                break
        except ValueError:
            continue
    if board is None:
        board = chess.Board()  # fallback to startpos

    records = []
    wtime, btime = BASE_TIME, BASE_TIME

    try:
        while not board.is_game_over(claim_draw=True):
            move_num = board.fullmove_number
            mat = material_count(board)

            limit = chess.engine.Limit(
                white_clock=wtime, white_inc=INCREMENT,
                black_clock=btime, black_inc=INCREMENT
            )

            t0 = time.time()
            result = engine.play(board, limit, info=chess.engine.INFO_SCORE)
            elapsed = time.time() - t0

            score = result.info.get("score")
            if score is None:
                break
            cp = score.white().score(mate_score=EVAL_CAP)
            if cp is None:
                break
            cp = max(-EVAL_CAP, min(EVAL_CAP, cp))

            records.append({"move": move_num, "material": mat, "eval": cp})

            if board.turn == chess.WHITE:
                wtime = max(0.0, wtime - elapsed + INCREMENT)
            else:
                btime = max(0.0, btime - elapsed + INCREMENT)

            board.push(result.move)

        outcome = board.outcome(claim_draw=True)
        if outcome is None:
            result_letter = None
        elif outcome.winner is True:
            result_letter = "W"
        elif outcome.winner is False:
            result_letter = "L"
        else:
            result_letter = "D"

    finally:
        engine.quit()

    if result_letter is None:
        return []

    return [{"move": r["move"], "material": r["material"],
              "eval": r["eval"], "result": result_letter} for r in records]


def worker(args):
    engine_path, fens = args
    try:
        return play_one_game(engine_path, fens)
    except Exception as e:
        print(f"game failed: {e}")
        return []


if __name__ == "__main__":
    download_book()
    fens = load_book_fens()
    print(f"Loaded {len(fens)} opening positions")

    out_file = OUT_DIR / "positions.jsonl"
    with mp.Pool(processes=CONCURRENCY) as pool, open(out_file, "w") as f:
        args = [(ENGINE_PATH, fens) for _ in range(N_GAMES)]
        for i, game_records in enumerate(pool.imap_unordered(worker, args)):
            for rec in game_records:
                f.write(json.dumps(rec) + "\n")
            if i % 5 == 0:
                print(f"{i}/{N_GAMES} games done")

    print(f"Done. Positions saved to {out_file}")