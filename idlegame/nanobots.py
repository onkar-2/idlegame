from idlegame.data import AutosavedPlayer
from enum import Enum
from idlegame import config
import time
import sys

class Nanotype(Enum):
    NORMAL = "normal"
    MINER = "miner"
    FIGHTER = "fighter"
    SUPER = "super"
    WARPER = "warper"
    RESEARCHER = "researcher"
    HACKER = "hacker"
    DIPLOMAT = "diplomat"

class Nanobot:
    def __init__(self, name: str, logic: str, type: Nanotype):
        self.name = name
        self.idle_action = None
        self.event_actions = {}
        self.type = type
        self.functional = True
        self.mining_rate = 1
        self.defense_rating = 1
        self.warp_chance = 0
        self.learn_rate = 0.2
        self.scan_success_rate = 0.01
        self.connection_rate = 0.1

        # Specialized nanobot attributes
        if self.type == Nanotype.MINER:
            self.mining_rate = 1.3
        elif self.type == Nanotype.FIGHTER:
            self.defense_rating = 1.3
        elif self.type == Nanotype.SUPER:
            self.mining_rate = 1.3
            self.defense_rating = 1.3
        elif self.type == Nanotype.WARPER:
            self.warp_chance = 0.1
        elif self.type == Nanotype.RESEARCHER:
            self.learn_rate = 0.5
        elif self.type == Nanotype.HACKER:
            self.scan_success_rate = 0.2
        elif self.type == Nanotype.DIPLOMAT:
            self.connection_rate = 0.3

        self.logic = logic.strip()
        self.complexity = 0
        self.update_complexity()
        self.parse_logic()

    def update_complexity(self):
        """Update complexity of the nanobot's logic."""
        self.complexity = (len(self.logic) / 10) * (2 if self.type != Nanotype.NORMAL else 1)

    def parse_logic(self):
        """Parse nanobot logic for idle and event-driven actions."""
        lines = self.logic.splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("idle "):
                self.idle_action = line[5:].strip()
            elif line.startswith("on "):
                parts = line[3:].split()
                if len(parts) >= 2:
                    self.event_actions[parts[0]] = parts[1]

    def get_current_action(self, event=None):
        """Determine the current action based on event or idle state."""
        if not self.functional:
            return "BROKEN"
        if event and event in self.event_actions:
            return f"Performing '{self.event_actions[event]}' due to event '{event}'"
        if self.idle_action:
            return f"Performing idle action: {self.idle_action}"
        return "IDLE"

def handle_nano(player: AutosavedPlayer, *args, **kwargs):
    """Create a new nanobot."""
    bot_type = kwargs.get('type', 'normal').upper()
    bot_name = kwargs.get('name')
    auto_accept = kwargs.get('y', False)

    if player.nano_cores.get('normal', 0) < 1:
        print("You need at least 1 normal nano core to create a new nanobot.")
        return
    
    if bot_type != 'NORMAL' and player.nano_cores.get(bot_type.lower(), 0) < 1:
        print(f"You need at least 1 {bot_type.lower()} core to create a specialized nanobot.")
        return
    
    nanobot_type = Nanotype[bot_type]

    if not auto_accept and input(f"Do you want to create a new {nanobot_type.name.lower()} nanobot? (yes/no): ").lower() not in ['yes', 'y']:
        print("No nanobot created.")
        return
    
    if not bot_name:
        bot_name = input("Enter a name for your nanobot: ")

    if len(bot_name) > 15:
        print("Error: Name too long (max 15 characters).")
        return

    if any(bot.name == bot_name for bot in player.nanobots):
        print(f"Error: Nanobot with the name '{bot_name}' already exists.")
        return

    print("Input your nanobot's logic (type 'done' to finish):")
    nano_logic = '\n'.join(iter(input, 'done')).strip()

    new_nanobot = Nanobot(name=bot_name, logic=nano_logic, type=nanobot_type)
    player.nanobots.append(new_nanobot)
    player.nano_cores['normal'] -= 1
    if bot_type != 'NORMAL':
        player.nano_cores[bot_type.lower()] -= 1
    player.save()

    print(f"Nanobot '{bot_name}' created!")

def handle_remove(player: AutosavedPlayer, *args, **kwargs):
    """Remove a nanobot and reclaim cores."""
    if len(args) == 0:
        print("Please provide the name of the nanobot to remove.")
        return

    bot_name = args[0]
    nanobot = next((bot for bot in player.nanobots if bot.name == bot_name), None)

    if nanobot is None:
        print(f"No nanobot found with the name '{bot_name}'.")
        return
    
    if not nanobot.functional:
        print("Cannot remove a broken nanobot.")
        return

    player.nano_cores['normal'] += 1
    if nanobot.type != Nanotype.NORMAL:
        player.nano_cores[nanobot.type.name.lower()] += 1

    player.nanobots.remove(nanobot)
    player.save()

    print(f"Nanobot '{bot_name}' removed and cores reclaimed.")

def handle_list(player: AutosavedPlayer, *args, **kwargs):
    """List all nanobots and their statuses."""
    if not player.nanobots:
        print("You have no nanobots.")
        return

    print(f"{'Name':<15}{'Type':<10}{'Idle':<15}{'Event Actions':<30}{'Current Action':<30}")
    print("-" * 100)

    for bot in player.nanobots:
        idle_action = bot.idle_action or "None"
        event_actions = ', '.join([f"{k}: {v}" for k, v in bot.event_actions.items()]) or "None"
        current_action = bot.get_current_action() or "None"
        print(f"{bot.name:<15}{bot.type.name:<10}{idle_action:<15}{event_actions:<30}{current_action:<30}")

    print("-" * 100)

def handle_fsck(player: AutosavedPlayer, *args, **kwargs):
    """Fix a broken nanobot using gold."""
    if len(args) == 0:
        print("Please provide the name of the nanobot to fix.")
        return
    
    bot_name = args[0]
    nanobot = next((bot for bot in player.nanobots if bot.name == bot_name), None)

    if nanobot is None:
        print(f"No nanobot found with the name '{bot_name}'.")
        return
    
    if nanobot.functional:
        print(f"Nanobot '{bot_name}' is already functional.")
        return

    quick_mode = kwargs.get('quick', False)
    auto_fix = kwargs.get('y', False)
    gold_required = 50 if not quick_mode else 20

    if player.gold < gold_required:
        print("Not enough gold to fix the nanobot.")
        return
    
    if not auto_fix:
        if input(f"Fix nanobot '{bot_name}' for {gold_required} gold? (yes/no): ").lower() not in ['yes', 'y']:
            print("Fix cancelled.")
            return

    player.gold -= gold_required
    animated_loading_bar(2 if quick_mode else 5)
    nanobot.functional = True
    player.save()

    print(f"Nanobot '{bot_name}' is now functional!")

def animated_loading_bar(duration: float):
    """Display a loading bar for a given duration."""
    total_length = 20
    for i in range(total_length + 1):
        bar = '#' * i + '-' * (total_length - i)
        sys.stdout.write(f'\r[{bar}] {i * 100 // total_length}%')
        sys.stdout.flush()
        time.sleep(duration / total_length)
    print()
