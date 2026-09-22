#!/usr/bin/env python3
"""
Community Minesweeper Engine for GitHub Profile README.
Handles game state, move validation, flood-fill revealing, win/loss detection,
and renders the interactive Markdown board.
"""

import sys
import os
import json
import random
from datetime import datetime, timezone

REPO_OWNER = "Howerchen666"
REPO_NAME = "Howerchen666"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "data", "minesweeper_state.json")
README_FILE = os.path.join(BASE_DIR, "README.md")

ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"]
COLS = ["1", "2", "3", "4", "5", "6", "7", "8"]
NUM_MINES = 8

NUMBER_EMOJIS = {
    0: "⬛",
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
}


def get_all_coords():
    coords = []
    for r in ROWS:
        for c in COLS:
            coords.append(f"{r}{c}")
    return coords


def get_neighbors(coord):
    r_idx = ROWS.index(coord[0])
    c_idx = COLS.index(coord[1])
    neighbors = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = r_idx + dr, c_idx + dc
            if 0 <= nr < len(ROWS) and 0 <= nc < len(COLS):
                neighbors.append(f"{ROWS[nr]}{COLS[nc]}")
    return neighbors


def initialize_new_game(preserved_stats=None):
    all_coords = get_all_coords()
    grid = {}
    for coord in all_coords:
        grid[coord] = {
            "revealed": False,
            "is_mine": False,
            "val": 0,
            "detonated": False,
        }

    stats = preserved_stats or {
        "total_games": 1,
        "community_wins": 0,
        "total_explosions": 0,
        "current_streak": 0,
        "best_streak": 0,
        "total_safe_tiles": 0,
    }

    state = {
        "status": "IN_PROGRESS",  # "IN_PROGRESS", "WON", "LOST"
        "first_click": True,
        "mines_count": NUM_MINES,
        "grid": grid,
        "moves_count": 0,
        "recent_moves": [],
        "stats": stats,
    }
    return state


def load_state():
    if not os.path.exists(STATE_FILE):
        state = initialize_new_game()
        save_state(state)
        return state
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading state: {e}. Initializing fresh game.")
        state = initialize_new_game()
        save_state(state)
        return state


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def place_mines_and_calc_vals(state, safe_coord):
    all_coords = get_all_coords()
    # Ensure safe_coord and ideally its immediate neighbors are safe on first click
    safe_zone = {safe_coord} | set(get_neighbors(safe_coord))
    candidates = [c for c in all_coords if c not in safe_zone]
    if len(candidates) < NUM_MINES:
        candidates = [c for c in all_coords if c != safe_coord]

    mines = random.sample(candidates, NUM_MINES)
    for m in mines:
        state["grid"][m]["is_mine"] = True

    # Compute adjacent mine counts
    for coord in all_coords:
        if not state["grid"][coord]["is_mine"]:
            adjacent_mines = sum(1 for n in get_neighbors(coord) if state["grid"][n]["is_mine"])
            state["grid"][coord]["val"] = adjacent_mines

    state["first_click"] = False


def make_issue_url(title, body):
    from urllib.parse import quote
    return f"https://github.com/{REPO_OWNER}/{REPO_NAME}/issues/new?title={quote(title)}&body={quote(body)}"


def execute_move(title, actor):
    state = load_state()
    parts = title.strip().split("|")
    action = parts[1].lower() if len(parts) > 1 else ""

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Handle Reset Action
    if action == "reset":
        stats = state.get("stats", {
            "total_games": 1,
            "community_wins": 0,
            "total_explosions": 0,
            "current_streak": 0,
            "best_streak": 0,
            "total_safe_tiles": 0,
        })
        stats["total_games"] = stats.get("total_games", 0) + 1
        stats.setdefault("current_streak", 0)
        stats.setdefault("best_streak", 0)
        stats.setdefault("total_safe_tiles", 0)
        state = initialize_new_game(preserved_stats=stats)
        state["recent_moves"].insert(0, {
            "actor": actor,
            "action": "reset",
            "coord": "-",
            "result": "Board reset for new match",
            "time": timestamp,
        })
        state["recent_moves"] = state["recent_moves"][:5]
        save_state(state)
        update_readme(state)
        return (
            f"### 🔄 Minesweeper Board Reset!\n\n"
            f"@{actor} has started a fresh community game! Good luck to the sweepers!"
        )

    # Handle Reveal Action
    if action == "reveal" and len(parts) > 2:
        coord = parts[2].upper()
        if coord not in state["grid"]:
            return f"❌ Invalid coordinate `{coord}`. Please select coordinates between A1 and H8."

        # If already over, prompt reset
        if state["status"] in ["WON", "LOST"]:
            reset_url = make_issue_url("minesweeper|reset", "Click Submit new issue to start a fresh game!")
            return (
                f"Game is already over ({state['status']})! "
                f"[Click here to start a new game]({reset_url})."
            )

        tile = state["grid"][coord]
        if tile["revealed"]:
            return f"Tile `{coord}` has already been revealed! Please pick another tile."

        # First click protection
        if state["first_click"]:
            place_mines_and_calc_vals(state, coord)

        state["moves_count"] = state.get("moves_count", 0) + 1
        tiles_cleared = 0

        # Check if hit mine
        if tile["is_mine"]:
            tile["revealed"] = True
            tile["detonated"] = True
            state["status"] = "LOST"
            stats = state.setdefault("stats", {})
            stats["total_explosions"] = stats.get("total_explosions", 0) + 1
            stats["current_streak"] = 0

            # Reveal all other mines
            for c, t in state["grid"].items():
                if t["is_mine"]:
                    t["revealed"] = True

            state["recent_moves"].insert(0, {
                "actor": actor,
                "action": "reveal",
                "coord": coord,
                "result": "💥 Detonated Mine! GAME OVER",
                "time": timestamp,
            })
            state["recent_moves"] = state["recent_moves"][:5]

            save_state(state)
            update_readme(state)
            reset_url = make_issue_url("minesweeper|reset", "Click Submit new issue to start a fresh game!")
            return (
                f"### 💥 BOOM! Detonation at `{coord}`!\n\n"
                f"Unfortunately, @{actor} hit a hidden mine at `{coord}`!\n\n"
                f"**Game Over!** [Click here to reset the board and try again]({reset_url})."
            )

        # Safe tile: BFS / Cascade zero-fill
        queue = [coord]
        tile["revealed"] = True
        tiles_cleared += 1

        while queue:
            curr = queue.pop(0)
            curr_tile = state["grid"][curr]
            if curr_tile["val"] == 0:
                for n in get_neighbors(curr):
                    n_tile = state["grid"][n]
                    if not n_tile["revealed"] and not n_tile["is_mine"]:
                        n_tile["revealed"] = True
                        tiles_cleared += 1
                        if n_tile["val"] == 0:
                            queue.append(n)

        # Update Team Safe Ground Stats
        stats = state.setdefault("stats", {})
        stats["total_safe_tiles"] = stats.get("total_safe_tiles", 0) + tiles_cleared

        # Check Win Condition
        all_coords = get_all_coords()
        non_mines_total = len(all_coords) - NUM_MINES
        revealed_count = sum(1 for c in all_coords if state["grid"][c]["revealed"] and not state["grid"][c]["is_mine"])

        if revealed_count >= non_mines_total:
            state["status"] = "WON"
            stats["community_wins"] = stats.get("community_wins", 0) + 1
            stats["current_streak"] = stats.get("current_streak", 0) + 1
            stats["best_streak"] = max(stats.get("best_streak", 0), stats["current_streak"])
            state["recent_moves"].insert(0, {
                "actor": actor,
                "action": "reveal",
                "coord": coord,
                "result": f"🏆 VICTORY! All safe tiles cleared!",
                "time": timestamp,
            })
            state["recent_moves"] = state["recent_moves"][:5]
            save_state(state)
            update_readme(state)
            reset_url = make_issue_url("minesweeper|reset", "Click Submit new issue to start a fresh game!")
            return (
                f"### 🏆 VICTORY! Minefield Cleared!\n\n"
                f"@{actor} revealed `{coord}` clearing the final safe tile!\n"
                f"The GitHub Community has conquered this minefield! 🎉\n\n"
                f"[Click here to start the next game]({reset_url})."
            )

        # Normal safe turn
        state["recent_moves"].insert(0, {
            "actor": actor,
            "action": "reveal",
            "coord": coord,
            "result": f"Safe ({tile['val']}) +{tiles_cleared} tiles",
            "time": timestamp,
        })
        state["recent_moves"] = state["recent_moves"][:5]
        save_state(state)
        update_readme(state)
        return (
            f"### 🟢 Safe Move at `{coord}`!\n\n"
            f"@{actor} revealed `{coord}` (Adjacent mines: **{tile['val']}**).\n"
            f"Total safe tiles uncovered in this turn: **{tiles_cleared}**.\n\n"
            f"Check the updated board on the [Profile README](https://github.com/{REPO_OWNER}/{REPO_NAME})!"
        )

    return f"❓ Unrecognized command: `{title}`. Supported formats: `minesweeper|reveal|C4` or `minesweeper|reset`."


def render_board_markdown(state):
    lines = []
    status = state["status"]
    reset_url = make_issue_url("minesweeper|reset", "Click Submit new issue to start a fresh game!")

    if status == "IN_PROGRESS":
        smiley = f"[ 🙂 Reset ]({reset_url})"
        status_badge = "🟢 In Progress"
    elif status == "WON":
        smiley = f"[ 😎 Won! Play Again ]({reset_url})"
        status_badge = "🏆 Victory!"
    else:
        smiley = f"[ 😵 Boom! Play Again ]({reset_url})"
        status_badge = "💥 Detonated"

    lines.append('<div align="center">')
    lines.append("")
    lines.append("### 💣 Community Minesweeper")
    lines.append(f"> 💣 **Mines:** `{NUM_MINES:02d}` &nbsp;&nbsp;|&nbsp;&nbsp; **{smiley}** &nbsp;&nbsp;|&nbsp;&nbsp; ⏱️ **Moves:** `{state.get('moves_count', 0):02d}` &nbsp;&nbsp;|&nbsp;&nbsp; {status_badge}")
    lines.append("")

    # Markdown Table
    col_header = "| | " + " | ".join(COLS) + " |"
    col_divider = "|:---:| " + " | ".join([":---:"] * len(COLS)) + " |"
    lines.append(col_header)
    lines.append(col_divider)

    for r in ROWS:
        row_cells = [f"**{r}**"]
        for c in COLS:
            coord = f"{r}{c}"
            tile = state["grid"].get(coord, {"revealed": False, "is_mine": False, "val": 0, "detonated": False})

            if tile["revealed"]:
                if tile.get("detonated", False):
                    cell = "💥"
                elif tile["is_mine"]:
                    cell = "💣"
                else:
                    cell = NUMBER_EMOJIS.get(tile["val"], "⬛")
            else:
                if status == "WON":
                    cell = "🚩"
                elif status == "LOST" and tile["is_mine"]:
                    cell = "💣"
                else:
                    reveal_url = make_issue_url(
                        f"minesweeper|reveal|{coord}",
                        f"Click 'Submit new issue' to reveal tile {coord}!"
                    )
                    cell = f"[⬜]({reveal_url})"
            row_cells.append(cell)
        lines.append("| " + " | ".join(row_cells) + " |")

    lines.append("")

    # Recent Activity
    lines.append("#### 📜 Recent Moves")
    lines.append("| Player | Tile | Result | Time |")
    lines.append("| :--- | :---: | :--- | :--- |")
    recent = state.get("recent_moves", [])
    if not recent:
        lines.append("| *None* | - | *Ready for first move!* | - |")
    else:
        for m in recent[:3]:
            user_link = f"[@{m['actor']}](https://github.com/{m['actor']})" if m['actor'] != "-" else "-"
            lines.append(f"| {user_link} | `{m['coord']}` | {m['result']} | {m['time']} |")

    # Community Team Records
    stats = state.get("stats", {})
    lines.append("")
    lines.append("#### 🌐 Team Records")
    lines.append(
        f"🏆 **Cleared:** `{stats.get('community_wins', 0)}` &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"🔥 **Streak:** `{stats.get('current_streak', 0)}` *(Best: {stats.get('best_streak', 0)})* &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"💥 **Explosions:** `{stats.get('total_explosions', 0)}` &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"🗺️ **Safe Tiles:** `{stats.get('total_safe_tiles', 0)}`"
    )
    lines.append("")
    lines.append("</div>")

    return "\n".join(lines)


def update_readme(state):
    if not os.path.exists(README_FILE):
        print("README.md not found, skipping README update.")
        return

    with open(README_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    start_tag = "<!-- MINESWEEPER_START -->"
    end_tag = "<!-- MINESWEEPER_END -->"

    if start_tag not in content or end_tag not in content:
        print("Minesweeper comment tags not found in README.md.")
        return

    board_md = render_board_markdown(state)
    before = content.split(start_tag)[0]
    after = content.split(end_tag)[1]

    new_content = f"{before}{start_tag}\n{board_md}\n{end_tag}{after}"

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully updated README.md with latest Minesweeper state.")


def main():
    if len(sys.argv) < 2:
        # Re-render or initialize
        state = load_state()
        update_readme(state)
        print("State loaded and README updated.")
        return

    arg = sys.argv[1]
    if arg in ["--render-only", "-r"]:
        state = load_state()
        update_readme(state)
        return

    title = arg
    actor = sys.argv[2] if len(sys.argv) > 2 else "anonymous"
    issue_number = sys.argv[3] if len(sys.argv) > 3 else ""

    result_comment = execute_move(title, actor)
    print(f"Outcome:\n{result_comment}")

    # Write comment to an output file for GitHub Action to read
    comment_file = os.path.join(BASE_DIR, "issue_comment.md")
    with open(comment_file, "w", encoding="utf-8") as f:
        f.write(result_comment)


if __name__ == "__main__":
    main()
