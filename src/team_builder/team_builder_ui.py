"""
team_builder_ui.py – Menu 4: UI tkinter để đọc team 6 Pokemon từ ảnh chụp.

Workflow:
  1. Paste/load ảnh team tổng (6 con) → OCR tên từng slot.
  2. Với mỗi Pokemon, paste/load ảnh màn hình Fight → OCR 4 move (tên + type + PP).
  3. Cho chỉnh sửa thủ công qua Text widget.
  4. Bấm Save → ghi src/config/team_party.json.

Format team_party.json:
[
  {
    "slot": 1,
    "name": "Gardevoir",
    "types": ["psychic", "fairy"],
    "moves": [
      {"name": "Surf", "type": "water", "power": 90, "accuracy": 100, "pp_current": 14, "pp_max": 15},
      ...
    ]
  },
  ...
]
"""

import difflib
import json
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageTk

# Whitelist Tesseract chỉ nhận chữ cái và dấu gạch ngang
_TESS_NAME_CFG = "--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- "

# Danh sách Pokemon Gen 1-9 thường gặp (dùng cho fuzzy match)
POKEMON_NAMES = [
    "Bulbasaur","Ivysaur","Venusaur","Charmander","Charmeleon","Charizard",
    "Squirtle","Wartortle","Blastoise","Caterpie","Metapod","Butterfree",
    "Weedle","Kakuna","Beedrill","Pidgey","Pidgeotto","Pidgeot",
    "Rattata","Raticate","Spearow","Fearow","Ekans","Arbok",
    "Pikachu","Raichu","Sandshrew","Sandslash","Nidoran","Nidorina",
    "Nidoqueen","Nidorino","Nidoking","Clefairy","Clefable",
    "Vulpix","Ninetales","Jigglypuff","Wigglytuff","Zubat","Golbat",
    "Oddish","Gloom","Vileplume","Paras","Parasect","Venonat","Venomoth",
    "Diglett","Dugtrio","Meowth","Persian","Psyduck","Golduck",
    "Mankey","Primeape","Growlithe","Arcanine","Poliwag","Poliwhirl",
    "Poliwrath","Abra","Kadabra","Alakazam","Machop","Machoke","Machamp",
    "Bellsprout","Weepinbell","Victreebel","Tentacool","Tentacruel",
    "Geodude","Graveler","Golem","Ponyta","Rapidash","Slowpoke","Slowbro",
    "Magnemite","Magneton","Farfetchd","Doduo","Dodrio","Seel","Dewgong",
    "Grimer","Muk","Shellder","Cloyster","Gastly","Haunter","Gengar",
    "Onix","Drowzee","Hypno","Krabby","Kingler","Voltorb","Electrode",
    "Exeggcute","Exeggutor","Cubone","Marowak","Hitmonlee","Hitmonchan",
    "Lickitung","Koffing","Weezing","Rhyhorn","Rhydon","Chansey",
    "Tangela","Kangaskhan","Horsea","Seadra","Goldeen","Seaking",
    "Staryu","Starmie","MrMime","Scyther","Jynx","Electabuzz","Magmar",
    "Pinsir","Tauros","Magikarp","Gyarados","Lapras","Ditto",
    "Eevee","Vaporeon","Jolteon","Flareon","Porygon","Omanyte","Omastar",
    "Kabuto","Kabutops","Aerodactyl","Snorlax","Articuno","Zapdos","Moltres",
    "Dratini","Dragonair","Dragonite","Mewtwo","Mew",
    "Chikorita","Bayleef","Meganium","Cyndaquil","Quilava","Typhlosion",
    "Totodile","Croconaw","Feraligatr","Sentret","Furret","Hoothoot","Noctowl",
    "Ledyba","Ledian","Spinarak","Ariados","Crobat","Chinchou","Lanturn",
    "Pichu","Cleffa","Igglybuff","Togepi","Togetic","Natu","Xatu",
    "Mareep","Flaaffy","Ampharos","Bellossom","Marill","Azumarill",
    "Sudowoodo","Politoed","Hoppip","Skiploom","Jumpluff","Aipom",
    "Sunkern","Sunflora","Yanma","Wooper","Quagsire","Espeon","Umbreon",
    "Murkrow","Slowking","Misdreavus","Unown","Wobbuffet","Girafarig",
    "Pineco","Forretress","Dunsparce","Gligar","Steelix","Snubbull",
    "Granbull","Qwilfish","Scizor","Shuckle","Heracross","Sneasel",
    "Teddiursa","Ursaring","Slugma","Magcargo","Swinub","Piloswine",
    "Corsola","Remoraid","Octillery","Delibird","Mantine","Skarmory",
    "Houndour","Houndoom","Kingdra","Phanpy","Donphan","Porygon2",
    "Stantler","Smeargle","Tyrogue","Hitmontop","Smoochum","Elekid",
    "Magby","Miltank","Blissey","Raikou","Entei","Suicune",
    "Larvitar","Pupitar","Tyranitar","Lugia","HoOh","Celebi",
    "Treecko","Grovyle","Sceptile","Torchic","Combusken","Blaziken",
    "Mudkip","Marshtomp","Swampert","Poochyena","Mightyena",
    "Zigzagoon","Linoone","Wurmple","Silcoon","Beautifly","Cascoon",
    "Dustox","Lotad","Lombre","Ludicolo","Seedot","Nuzleaf","Shiftry",
    "Taillow","Swellow","Wingull","Pelipper","Ralts","Kirlia","Gardevoir",
    "Surskit","Masquerain","Shroomish","Breloom","Slakoth","Vigoroth",
    "Slaking","Nincada","Ninjask","Shedinja","Whismur","Loudred","Exploud",
    "Makuhita","Hariyama","Azurill","Nosepass","Skitty","Delcatty",
    "Sableye","Mawile","Aron","Lairon","Aggron","Meditite","Medicham",
    "Electrike","Manectric","Plusle","Minun","Volbeat","Illumise",
    "Roselia","Gulpin","Swalot","Carvanha","Sharpedo","Wailmer","Wailord",
    "Numel","Camerupt","Torkoal","Spoink","Grumpig","Spinda",
    "Trapinch","Vibrava","Flygon","Cacnea","Cacturne","Swablu","Altaria",
    "Zangoose","Seviper","Lunatone","Solrock","Barboach","Whiscash",
    "Corphish","Crawdaunt","Baltoy","Claydol","Lileep","Cradily",
    "Anorith","Armaldo","Feebas","Milotic","Castform","Kecleon",
    "Shuppet","Banette","Duskull","Dusclops","Tropius","Chimecho",
    "Absol","Wynaut","Snorunt","Glalie","Spheal","Sealeo","Walrein",
    "Clamperl","Huntail","Gorebyss","Relicanth","Luvdisc","Bagon",
    "Shelgon","Salamence","Beldum","Metang","Metagross",
    "Regirock","Regice","Registeel","Latias","Latios","Kyogre",
    "Groudon","Rayquaza","Jirachi","Deoxys",
    "Turtwig","Grotle","Torterra","Chimchar","Monferno","Infernape",
    "Piplup","Prinplup","Empoleon","Starly","Staravia","Staraptor",
    "Bidoof","Bibarel","Kricketot","Kricketune","Shinx","Luxio","Luxray",
    "Budew","Roserade","Cranidos","Rampardos","Shieldon","Bastiodon",
    "Burmy","Wormadam","Mothim","Combee","Vespiquen","Pachirisu",
    "Buizel","Floatzel","Cherubi","Cherrim","Shellos","Gastrodon",
    "Ambipom","Drifloon","Drifblim","Buneary","Lopunny",
    "Mismagius","Honchkrow","Glameow","Purugly","Chingling",
    "Stunky","Skuntank","Bronzor","Bronzong","Bonsly","Mime Jr",
    "Happiny","Chatot","Spiritomb","Gible","Gabite","Garchomp",
    "Munchlax","Riolu","Lucario","Hippopotas","Hippowdon",
    "Skorupi","Drapion","Croagunk","Toxicroak","Carnivine",
    "Finneon","Lumineon","Mantyke","Snover","Abomasnow","Weavile",
    "Magnezone","Lickilicky","Rhyperior","Tangrowth","Electivire",
    "Magmortar","Togekiss","Yanmega","Leafeon","Glaceon",
    "Gliscor","Mamoswine","Porygon-Z","Gallade","Probopass",
    "Dusknoir","Froslass","Rotom","Uxie","Mesprit","Azelf",
    "Dialga","Palkia","Heatran","Regigigas","Giratina","Cresselia",
    "Phione","Manaphy","Darkrai","Shaymin","Arceus",
    "Victini","Snivy","Servine","Serperior","Tepig","Pignite","Emboar",
    "Oshawott","Dewott","Samurott","Patrat","Watchog","Lillipup",
    "Herdier","Stoutland","Purrloin","Liepard","Pansage","Simisage",
    "Pansear","Simisear","Panpour","Simipour","Munna","Musharna",
    "Pidove","Tranquill","Unfezant","Blitzle","Zebstrika",
    "Roggenrola","Boldore","Gigalith","Woobat","Swoobat",
    "Drilbur","Excadrill","Audino","Timburr","Gurdurr","Conkeldurr",
    "Tympole","Palpitoad","Seismitoad","Throh","Sawk",
    "Sewaddle","Swadloon","Leavanny","Venipede","Whirlipede","Scolipede",
    "Cottonee","Whimsicott","Petilil","Lilligant","Basculin",
    "Sandile","Krokorok","Krookodile","Darumaka","Darmanitan",
    "Maractus","Dwebble","Crustle","Scraggy","Scrafty",
    "Sigilyph","Yamask","Cofagrigus","Tirtouga","Carracosta",
    "Archen","Archeops","Trubbish","Garbodor","Zorua","Zoroark",
    "Minccino","Cinccino","Gothita","Gothorita","Gothitelle",
    "Solosis","Duosion","Reuniclus","Ducklett","Swanna",
    "Vanillite","Vanillish","Vanilluxe","Deerling","Sawsbuck",
    "Emolga","Karrablast","Escavalier","Foongus","Amoonguss",
    "Frillish","Jellicent","Alomomola","Joltik","Galvantula",
    "Ferroseed","Ferrothorn","Klink","Klang","Klinklang",
    "Tynamo","Eelektrik","Eelektross","Elgyem","Beheeyem",
    "Litwick","Lampent","Chandelure","Axew","Fraxure","Haxorus",
    "Cubchoo","Beartic","Cryogonal","Shelmet","Accelgor",
    "Stunfisk","Mienfoo","Mienshao","Druddigon","Golett","Golurk",
    "Pawniard","Bisharp","Bouffalant","Rufflet","Braviary",
    "Vullaby","Mandibuzz","Heatmor","Durant","Deino","Zweilous","Hydreigon",
    "Larvesta","Volcarona","Cobalion","Terrakion","Virizion",
    "Tornadus","Thundurus","Reshiram","Zekrom","Landorus","Kyurem",
    "Keldeo","Meloetta","Genesect",
    "Chespin","Quilladin","Chesnaught","Fennekin","Braixen","Delphox",
    "Froakie","Frogadier","Greninja","Bunnelby","Diggersby",
    "Fletchling","Fletchinder","Talonflame","Scatterbug","Spewpa","Vivillon",
    "Litleo","Pyroar","Flabebe","Floette","Florges",
    "Skiddo","Gogoat","Pancham","Pangoro","Furfrou",
    "Espurr","Meowstic","Honedge","Doublade","Aegislash",
    "Spritzee","Aromatisse","Swirlix","Slurpuff","Inkay","Malamar",
    "Binacle","Barbaracle","Skrelp","Dragalge","Clauncher","Clawitzer",
    "Helioptile","Heliolisk","Tyrunt","Tyrantrum","Amaura","Aurorus",
    "Sylveon","Hawlucha","Dedenne","Carbink","Goomy","Sliggoo","Goodra",
    "Klefki","Phantump","Trevenant","Pumpkaboo","Gourgeist",
    "Bergmite","Avalugg","Noibat","Noivern","Xerneas","Yveltal","Zygarde",
    "Diancie","Hoopa","Volcanion",
    "Rowlet","Dartrix","Decidueye","Litten","Torracat","Incineroar",
    "Popplio","Brionne","Primarina","Pikipek","Trumbeak","Toucannon",
    "Yungoos","Gumshoos","Grubbin","Charjabug","Vikavolt",
    "Crabrawler","Crabominable","Oricorio","Cutiefly","Ribombee",
    "Rockruff","Lycanroc","Wishiwashi","Mareanie","Toxapex",
    "Mudbray","Mudsdale","Dewpider","Araquanid","Fomantis","Lurantis",
    "Morelull","Shiinotic","Salandit","Salazzle","Stufful","Bewear",
    "Bounsweet","Steenee","Tsareena","Comfey","Oranguru","Passimian",
    "Wimpod","Golisopod","Sandygast","Palossand","Pyukumuku","TypeNull",
    "Silvally","Minior","Komala","Turtonator","Togedemaru","Mimikyu",
    "Bruxish","Drampa","Dhelmise","Jangmo-o","Hakamo-o","Kommo-o",
    "Tapu Koko","Tapu Lele","Tapu Bulu","Tapu Fini",
    "Cosmog","Cosmoem","Solgaleo","Lunala","Nihilego","Buzzwole",
    "Pheromosa","Xurkitree","Celesteela","Kartana","Guzzlord",
    "Necrozma","Magearna","Marshadow","Poipole","Naganadel",
    "Stakataka","Blacephalon","Zeraora","Meltan","Melmetal",
    "Grookey","Thwackey","Rillaboom","Scorbunny","Raboot","Cinderace",
    "Sobble","Drizzile","Inteleon","Skwovet","Greedent",
    "Rookidee","Corvisquire","Corviknight","Blipbug","Dottler","Orbeetle",
    "Nickit","Thievul","Gossifleur","Eldegoss","Wooloo","Dubwool",
    "Chewtle","Drednaw","Yamper","Boltund","Rolycoly","Carkol","Coalossal",
    "Applin","Flapple","Appletun","Silicobra","Sandaconda",
    "Cramorant","Arrokuda","Barraskewda","Toxel","Toxtricity",
    "Sizzlipede","Centiskorch","Clobbopus","Grapploct","Sinistea","Polteageist",
    "Hatenna","Hattrem","Hatterene","Impidimp","Morgrem","Grimmsnarl",
    "Obstagoon","Perrserker","Cursola","Sirfetchd","MrRime","Runerigus",
    "Milcery","Alcremie","Falinks","Pincurchin","Snom","Frosmoth",
    "Stonjourner","Eiscue","Indeedee","Morpeko","Cufant","Copperajah",
    "Dracozolt","Arctozolt","Dracovish","Arctovish","Duraludon",
    "Dreepy","Drakloak","Dragapult",
    "Zacian","Zamazenta","Eternatus","Kubfu","Urshifu","Zarude",
    "Regieleki","Regidrago","Glastrier","Spectrier","Calyrex",
    "Wyrdeer","Kleavor","Ursaluna","Basculegion","Sneasler","Overqwil",
    "Enamorus","Sprigatito","Floragato","Meowscarada",
    "Fuecoco","Crocalor","Skeledirge","Quaxly","Quaxwell","Quaquaval",
    "Lechonk","Oinkologne","Tarountula","Spidops","Nymble","Lokix",
    "Pawmi","Pawmo","Pawmot","Tandemaus","Maushold",
    "Fidough","Dachsbun","Smoliv","Dolliv","Arboliva",
    "Squawkabilly","Nacli","Naclstack","Garganacl",
    "Charcadet","Armarouge","Ceruledge","Tadbulb","Bellibolt",
    "Wattrel","Kilowattrel","Maschiff","Mabosstiff",
    "Shroodle","Grafaiai","Bramblin","Brambleghast",
    "Toedscool","Toedscruel","Klawf","Capsakid","Scovillain",
    "Rellor","Rabsca","Flittle","Espathra","Tinkatink","Tinkatuff","Tinkaton",
    "Wiglett","Wugtrio","Bombirdier","Finizen","Palafin",
    "Varoom","Revavroom","Cyclizar","Orthworm","Glimmet","Glimmora",
    "Greavard","Houndstone","Flamigo","Cetoddle","Cetitan",
    "Veluza","Dondozo","Tatsugiri","Annihilape",
    "Clodsire","Farigiraf","Dudunsparce","Kingambit",
    "Great Tusk","Scream Tail","Brute Bonnet","Flutter Mane",
    "Slither Wing","Sandy Shocks","Iron Treads","Iron Bundle",
    "Iron Hands","Iron Jugulis","Iron Moth","Iron Thorns",
    "Frigibax","Arctibax","Baxcalibur","Gimmighoul","Gholdengo",
    "Wo-Chien","Chien-Pao","Ting-Lu","Chi-Yu",
    "Roaring Moon","Iron Valiant","Koraidon","Miraidon",
    "Walking Wake","Iron Leaves","Dipplin","Poltchageist","Sinistcha",
    "Okidogi","Munkidori","Fezandipiti","Ogerpon","Archaludon",
    "Hydrapple","Gouging Fire","Raging Bolt","Iron Boulder","Iron Crown",
    "Terapagos","Pecharunt",
]

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "src" / "config" / "tool_config.json"
TEAM_PATH = ROOT / "src" / "config" / "team_party.json"
DATA_DIR = ROOT / "src" / "data"
POKEMON_CACHE_DIR = DATA_DIR / "pokeapi_cache" / "pokemon"
MOVE_CACHE_DIR = DATA_DIR / "pokeapi_cache" / "moves"

# Đảm bảo thư mục tồn tại
for _d in (POKEMON_CACHE_DIR, MOVE_CACHE_DIR, ROOT / "src" / "runtime"):
    _d.mkdir(parents=True, exist_ok=True)

# ---------- move data tĩnh (power / accuracy / type) để không cần PokeAPI cho move phổ biến ----------
KNOWN_MOVES: dict = {}

_KNOWN_MOVES_INLINE = [
    # name, type, power, accuracy
    ("Surf", "water", 90, 100),
    ("Ice Beam", "ice", 90, 100),
    ("Thunderbolt", "electric", 90, 100),
    ("Flamethrower", "fire", 90, 100),
    ("Shadow Ball", "ghost", 80, 100),
    ("Energy Ball", "grass", 90, 100),
    ("Psychic", "psychic", 90, 100),
    ("Dark Pulse", "dark", 80, 100),
    ("Moonblast", "fairy", 95, 100),
    ("Dazzling Gleam", "fairy", 80, 100),
    ("Hyper Beam", "normal", 150, 90),
    ("Giga Impact", "normal", 150, 90),
    ("Earthquake", "ground", 100, 100),
    ("Rock Slide", "rock", 75, 90),
    ("Stone Edge", "rock", 100, 80),
    ("Close Combat", "fighting", 120, 100),
    ("Brick Break", "fighting", 75, 100),
    ("Focus Blast", "fighting", 120, 70),
    ("Aura Sphere", "fighting", 80, 100),
    ("Drain Punch", "fighting", 75, 100),
    ("Fire Blast", "fire", 110, 85),
    ("Blizzard", "ice", 110, 70),
    ("Thunder", "electric", 110, 70),
    ("Hurricane", "flying", 110, 70),
    ("Brave Bird", "flying", 120, 100),
    ("Aerial Ace", "flying", 60, 100),
    ("Fly", "flying", 90, 95),
    ("Air Slash", "flying", 75, 95),
    ("Outrage", "dragon", 120, 100),
    ("Dragon Pulse", "dragon", 85, 100),
    ("Draco Meteor", "dragon", 130, 90),
    ("Body Slam", "normal", 85, 100),
    ("Return", "normal", 102, 100),
    ("Waterfall", "water", 80, 100),
    ("Aqua Tail", "water", 90, 90),
    ("Scald", "water", 80, 100),
    ("Water Pulse", "water", 60, 100),
    ("Hydro Pump", "water", 110, 80),
    ("Gunk Shot", "poison", 120, 80),
    ("Poison Jab", "poison", 80, 100),
    ("Cross Poison", "poison", 70, 100),
    ("Sludge Bomb", "poison", 90, 100),
    ("Crunch", "dark", 80, 100),
    ("Bite", "dark", 60, 100),
    ("Night Slash", "dark", 70, 100),
    ("Leaf Blade", "grass", 90, 100),
    ("Wood Hammer", "grass", 120, 100),
    ("Seed Bomb", "grass", 80, 100),
    ("Power Whip", "grass", 120, 85),
    ("Flash Cannon", "steel", 80, 100),
    ("Iron Head", "steel", 80, 100),
    ("Meteor Mash", "steel", 90, 90),
    ("Bullet Punch", "steel", 40, 100),
    ("Iron Tail", "steel", 100, 75),
    ("Flame Charge", "fire", 50, 100),
    ("Fire Punch", "fire", 75, 100),
    ("Ice Punch", "ice", 75, 100),
    ("Thunder Punch", "electric", 75, 100),
    ("Discharge", "electric", 80, 100),
    ("Wild Charge", "electric", 90, 100),
    ("Volt Switch", "electric", 70, 100),
    ("Play Rough", "fairy", 90, 90),
    ("Psycho Cut", "psychic", 70, 100),
    ("Future Sight", "psychic", 120, 100),
    ("Zen Headbutt", "psychic", 80, 90),
    ("Bug Buzz", "bug", 90, 100),
    ("X-Scissor", "bug", 80, 100),
    ("Signal Beam", "bug", 75, 100),
    ("Lunge", "bug", 80, 100),
    ("Phantom Force", "ghost", 90, 100),
    ("Shadow Claw", "ghost", 70, 100),
    ("Hex", "ghost", 65, 100),
    ("Sucker Punch", "dark", 70, 100),
    ("Superpower", "fighting", 120, 100),
    ("Hi Jump Kick", "fighting", 130, 90),
    ("Jump Kick", "fighting", 100, 95),
    ("Gyro Ball", "steel", 150, 100),
    ("Heavy Slam", "steel", 100, 100),
    ("Explosion", "normal", 250, 100),
    ("Self-Destruct", "normal", 200, 100),
    ("Megahorn", "bug", 120, 85),
    ("Dig", "ground", 80, 100),
    ("Bulldoze", "ground", 60, 100),
    ("High Horsepower", "ground", 95, 95),
    ("Earth Power", "ground", 90, 100),
    ("Dive", "water", 80, 100),
    ("Aurora Beam", "ice", 65, 100),
    ("Icicle Crash", "ice", 85, 90),
    ("Icicle Spear", "ice", 25, 100),
    ("Avalanche", "ice", 60, 100),
    ("Night Daze", "dark", 85, 95),
    ("Foul Play", "dark", 95, 100),
    ("Assurance", "dark", 60, 100),
    ("Flare Blitz", "fire", 120, 100),
    ("Heat Wave", "fire", 95, 90),
    ("Overheat", "fire", 130, 90),
    ("Dragon Claw", "dragon", 80, 100),
    ("Dragon Rush", "dragon", 100, 75),
    ("Twister", "dragon", 40, 100),
    ("Petal Blizzard", "grass", 90, 100),
    ("Grass Knot", "grass", 0, 100),
    ("Giga Drain", "grass", 75, 100),
    ("Snarl", "dark", 55, 95),
    ("Rock Blast", "rock", 25, 90),
    ("Power Gem", "rock", 80, 100),
    ("Smart Strike", "steel", 70, 100),
    ("Comet Punch", "normal", 18, 85),
    ("Double-Edge", "normal", 120, 100),
    ("Hyper Fang", "normal", 80, 90),
    ("Quick Attack", "normal", 40, 100),
    ("Extreme Speed", "normal", 80, 100),
    ("Facade", "normal", 70, 100),
    ("Tackle", "normal", 40, 100),
    ("Scratch", "normal", 40, 100),
    ("Pound", "normal", 40, 100),
    ("Cut", "normal", 50, 95),
    ("Swift", "normal", 60, 100),
    ("Slash", "normal", 70, 100),
    ("Headbutt", "normal", 70, 100),
    ("Take Down", "normal", 90, 85),
    ("Rollout", "rock", 30, 90),
    ("Rock Throw", "rock", 50, 90),
    ("Rock Tomb", "rock", 60, 95),
    ("Ancient Power", "rock", 60, 100),
    ("Psybeam", "psychic", 65, 100),
    ("Stored Power", "psychic", 20, 100),
    ("Confusion", "psychic", 50, 100),
    ("Extrasensory", "psychic", 80, 100),
    ("Luster Purge", "psychic", 70, 100),
    ("Mist Ball", "psychic", 70, 100),
    ("Muddy Water", "water", 90, 85),
    ("Mud Shot", "ground", 55, 95),
    ("Mud-Slap", "ground", 20, 100),
    ("Sand Tomb", "ground", 35, 85),
    ("Poison Fang", "poison", 50, 100),
    ("Acid Spray", "poison", 40, 100),
    ("Clear Smog", "poison", 50, 100),
    ("Venoshock", "poison", 65, 100),
    ("Peck", "flying", 35, 100),
    ("Wing Attack", "flying", 60, 100),
    ("Sky Attack", "flying", 140, 90),
    ("Pluck", "flying", 60, 100),
    ("Leaf Storm", "grass", 130, 90),
    ("Petal Dance", "grass", 120, 100),
    ("Solar Beam", "grass", 120, 100),
    ("Razor Leaf", "grass", 55, 95),
    ("Ember", "fire", 40, 100),
    ("Flame Wheel", "fire", 60, 100),
    ("Incinerate", "fire", 60, 100),
    ("Lava Plume", "fire", 80, 100),
    ("Magma Storm", "fire", 100, 75),
    ("Sacred Fire", "fire", 100, 95),
    ("Water Gun", "water", 40, 100),
    ("Bubble Beam", "water", 65, 100),
    ("Brine", "water", 65, 100),
    ("Sparkling Aria", "water", 90, 100),
    ("Crabhammer", "water", 100, 90),
    ("Liquidation", "water", 85, 100),
    ("Clamp", "water", 35, 85),
    ("Frost Breath", "ice", 60, 90),
    ("Glaciate", "ice", 65, 95),
    ("Freeze Dry", "ice", 70, 100),
    ("Ice Fang", "ice", 65, 95),
    ("Powder Snow", "ice", 40, 100),
    ("Sheer Cold", "ice", 0, 30),
    ("Thundershock", "electric", 40, 100),
    ("Shock Wave", "electric", 60, 100),
    ("Spark", "electric", 65, 100),
    ("Charge Beam", "electric", 50, 90),
    ("Electro Ball", "electric", 0, 100),
    ("Zap Cannon", "electric", 120, 50),
    ("Nuzzle", "electric", 20, 100),
    ("Karate Chop", "fighting", 50, 100),
    ("Mach Punch", "fighting", 40, 100),
    ("Sky Uppercut", "fighting", 85, 90),
    ("Vital Throw", "fighting", 70, 100),
    ("Seismic Toss", "fighting", 0, 100),
    ("Force Palm", "fighting", 60, 100),
    ("Smelling Salts", "normal", 70, 100),
    ("Bone Rush", "ground", 25, 90),
    ("Bone Club", "ground", 65, 85),
    ("Bonemerang", "ground", 50, 90),
    ("Rock Wrecker", "rock", 150, 90),
    ("Head Smash", "rock", 150, 80),
    ("Diamond Storm", "rock", 100, 95),
    ("Boomburst", "normal", 140, 100),
    ("Hyper Voice", "normal", 90, 100),
    ("Round", "normal", 60, 100),
    ("Echoed Voice", "normal", 40, 100),
    ("Recover", "normal", 0, 100),
    ("Roost", "flying", 0, 100),
    ("Soft-Boiled", "normal", 0, 100),
    ("Slack Off", "normal", 0, 100),
    ("Morning Sun", "normal", 0, 100),
    ("Moonlight", "fairy", 0, 100),
    ("Synthesis", "grass", 0, 100),
    ("Wish", "normal", 0, 100),
    ("Toxic", "poison", 0, 90),
    ("Will-O-Wisp", "fire", 0, 85),
    ("Thunder Wave", "electric", 0, 90),
    ("Glare", "normal", 0, 100),
    ("Spore", "grass", 0, 100),
    ("Sleep Powder", "grass", 0, 75),
    ("Stun Spore", "grass", 0, 75),
    ("Attract", "normal", 0, 100),
    ("Confuse Ray", "ghost", 0, 100),
    ("Swagger", "normal", 0, 85),
    ("Swords Dance", "normal", 0, 100),
    ("Calm Mind", "psychic", 0, 100),
    ("Nasty Plot", "dark", 0, 100),
    ("Dragon Dance", "dragon", 0, 100),
    ("Quiver Dance", "bug", 0, 100),
    ("Shell Smash", "normal", 0, 100),
    ("Agility", "psychic", 0, 100),
    ("Bulk Up", "fighting", 0, 100),
    ("Coil", "poison", 0, 100),
    ("Hone Claws", "dark", 0, 100),
    ("Work Up", "normal", 0, 100),
    ("Stealth Rock", "rock", 0, 100),
    ("Spikes", "ground", 0, 100),
    ("Toxic Spikes", "poison", 0, 100),
    ("Sticky Web", "bug", 0, 100),
    ("Reflect", "psychic", 0, 100),
    ("Light Screen", "psychic", 0, 100),
    ("Aurora Veil", "ice", 0, 100),
    ("Substitute", "normal", 0, 100),
    ("Protect", "normal", 0, 100),
    ("Detect", "fighting", 0, 100),
    ("Endure", "normal", 0, 100),
    ("Baton Pass", "normal", 0, 100),
    ("U-turn", "bug", 70, 100),
    ("Volt Switch", "electric", 70, 100),
    ("Flip Turn", "water", 60, 100),
    ("Parting Shot", "dark", 0, 100),
    ("Defog", "flying", 0, 100),
    ("Rapid Spin", "normal", 50, 100),
    ("Trick", "psychic", 0, 100),
    ("Knock Off", "dark", 65, 100),
    ("Trick Room", "psychic", 0, 100),
    ("Magic Room", "psychic", 0, 100),
    ("Wonder Room", "psychic", 0, 100),
]

for _m in _KNOWN_MOVES_INLINE:
    KNOWN_MOVES[_m[0].lower()] = {"type": _m[1], "power": _m[2], "accuracy": _m[3]}


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_team() -> list:
    if TEAM_PATH.exists():
        with TEAM_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_team(team: list):
    TEAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TEAM_PATH.open("w", encoding="utf-8") as f:
        json.dump(team, f, indent=2, ensure_ascii=False)


def init_tesseract(config):
    cmd = config.get("ocr", {}).get("tesseract_cmd", "").strip()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


def preprocess(img_bgr, scale=3):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def ocr_single_line(img_bgr, config, psm=7) -> str:
    processed = preprocess(img_bgr)
    pil = Image.fromarray(processed)
    lang = config.get("ocr", {}).get("language", "eng")
    return pytesseract.image_to_string(pil, lang=lang, config=f"--psm {psm}").strip()


def ocr_block(img_bgr, config, psm=6) -> str:
    processed = preprocess(img_bgr)
    pil = Image.fromarray(processed)
    lang = config.get("ocr", {}).get("language", "eng")
    return pytesseract.image_to_string(pil, lang=lang, config=f"--psm {psm}").strip()


def load_image_cv2(path: str):
    arr = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def parse_pp(text: str):
    """Trích PP từ chuỗi kiểu '14/15' → (14, 15)"""
    m = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def parse_move_name(text: str) -> str:
    """Làm sạch tên move từ OCR output"""
    cleaned = re.sub(r"[^A-Za-z0-9 '\-]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Loại bỏ các từ nhiễu phổ biến
    cleaned = re.sub(r"\b(pp|type|power|acc)\b", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def guess_move_data(name: str) -> dict:
    """Tra cứu move data từ bảng tĩnh"""
    key = name.strip().lower()
    if key in KNOWN_MOVES:
        return dict(KNOWN_MOVES[key])
    # Thử tìm move gần nhất (partial match)
    for k, v in KNOWN_MOVES.items():
        if key in k or k in key:
            return dict(v)
    return {"type": "normal", "power": 0, "accuracy": 100}


def ocr_variants(img_bgr, config, psm=7, name_mode=False) -> str:
    """
    Thử nhiều cách preprocess và trả về kết quả OCR hợp lệ nhất.
    name_mode=True: dùng whitelist chỉ chữ cái (tốt cho OCR tên Pokemon).
    """
    lang = config.get("ocr", {}).get("language", "eng")
    tess_cfg = _TESS_NAME_CFG if name_mode else f"--psm {psm} --oem 3"
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    big  = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    variants = [
        cv2.threshold(big, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],  # nền tối (game UI)
        cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],      # OTSU thường
        cv2.threshold(big, 180, 255, cv2.THRESH_BINARY)[1],                       # ngưỡng cao (chữ trắng)
        cv2.threshold(big, 80,  255, cv2.THRESH_BINARY_INV)[1],                   # đảo ngưỡng thấp
        big,                                                                       # grayscale thô
    ]

    best = ""
    for v in variants:
        txt = pytesseract.image_to_string(
            Image.fromarray(v), lang=lang, config=tess_cfg
        ).strip()
        letters_in_best = sum(c.isalpha() for c in best)
        letters_in_txt  = sum(c.isalpha() for c in txt)
        if letters_in_txt > letters_in_best:
            best = txt
    return best


def fuzzy_match_pokemon(raw: str) -> str:
    """
    So sánh chuỗi OCR với danh sách Pokemon, trả về tên gần nhất.
    Nếu độ khớp thấp hơn 0.55 thì trả về chuỗi gốc đã làm sạch.
    """
    if not raw or len(raw) < 3:
        return raw
    raw_lower = raw.lower()
    names_lower = [n.lower() for n in POKEMON_NAMES]
    matches = difflib.get_close_matches(raw_lower, names_lower, n=1, cutoff=0.55)
    if matches:
        idx = names_lower.index(matches[0])
        return POKEMON_NAMES[idx]
    return raw


def extract_pokemon_name_from_ocr(text: str) -> str:
    """
    Trích tên Pokemon từ chuỗi OCR của 1 slot team.
    Bỏ qua dòng chứa Lv, số thuần, ký tự đặc biệt.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines:
        cleaned = re.sub(r'\bLv\.?\s*\d+\b', '', line, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^A-Za-z\s\-']", '', cleaned).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        noise_words = {'lv', 'hp', 'pp', 'ok', 'no', 'is', 'the', 'and'}
        if len(cleaned) >= 3 and cleaned.lower() not in noise_words:
            return cleaned
    return ''


def ocr_team_from_image(img_bgr, config) -> list:
    """
    OCR ảnh team panel (6 slot dọc).
    Layout mỗi slot: [sprite trái ~45%] [tên Pokemon + Lv.xx bên phải]
    Dùng whitelist chỉ chữ cái + fuzzy match với danh sách Pokemon.
    """
    h, w = img_bgr.shape[:2]
    slot_h = h // 6
    names = []

    for i in range(6):
        y_start = i * slot_h
        y_end   = min((i + 1) * slot_h, h)

        # Sprite chiếm ~45% bên trái → lấy từ 45% trở đi cho tên
        x_start = int(w * 0.45)
        slot_crop = img_bgr[y_start:y_end, x_start:]

        # Tên thường ở phần trên mỗi slot (50-60% cao)
        sh = slot_crop.shape[0]
        name_row = slot_crop[:max(int(sh * 0.55), 1), :]

        # OCR với whitelist chữ cái
        text = ocr_variants(name_row, config, psm=7, name_mode=True)
        if not text.strip():
            text = ocr_variants(slot_crop, config, psm=7, name_mode=True)

        raw_name = extract_pokemon_name_from_ocr(text)
        # Fuzzy match với danh sách Pokemon thật
        matched = fuzzy_match_pokemon(raw_name)
        names.append(normalize(matched))

    return names


def ocr_moves_from_fight_image(img_bgr, config) -> list:
    """
    OCR ảnh panel Fight (4 dòng dọc).
    Layout thực tế: mỗi dòng = [Tên move (trái)] [PP current/max (phải)]
    Ví dụ:  Surf       15/15
            Ice Beam   16/16
            Toxic      10/10
            Recover     8/8
    Chia ảnh thành 4 strip ngang bằng nhau, mỗi strip OCR riêng.
    """
    h, w = img_bgr.shape[:2]
    row_h = h // 4

    moves = []
    for i in range(4):
        y1 = i * row_h
        y2 = min((i + 1) * row_h, h)
        row = img_bgr[y1:y2, :]

        rh, rw = row.shape[:2]
        # Cột tên: 65% bên trái (tránh bị nhiễu bởi số PP)
        name_cell = row[:, : int(rw * 0.65)]
        # Cột PP: 35% bên phải
        pp_cell   = row[:, int(rw * 0.60):]

        # OCR tên move (psm=7 = single line)
        name_text = ocr_single_line(name_cell, config, psm=7)
        move_name = parse_move_name(name_text)

        # OCR PP (psm=7)
        pp_text = ocr_single_line(pp_cell, config, psm=7)
        # fallback: OCR toàn dòng để tìm PP nếu cột PP trống
        if not re.search(r"\d+/\d+", pp_text):
            full_text = ocr_single_line(row, config, psm=7)
            pp_text = full_text

        pp_current, pp_max = parse_pp(pp_text)

        # Tra cứu data move từ bảng tĩnh
        data = guess_move_data(move_name)

        moves.append({
            "name": normalize(move_name) if move_name else f"Move{i+1}",
            "type": data.get("type", "normal"),
            "power": data.get("power", 0),
            "accuracy": data.get("accuracy", 100),
            "pp_current": pp_current if pp_current is not None else pp_max,
            "pp_max": pp_max,
        })

    return moves


# ========================= GUI =========================

class TeamBuilderApp(tk.Frame):
    def __init__(self, master, config):
        super().__init__(master, bg="#1e1e2e")
        self.config_data = config
        self.master_window = master if isinstance(master, tk.Tk) else master.winfo_toplevel()
        
        # State
        self.current_pokemon_index = 0  # 0..5
        self.team = load_team()
        # Đảm bảo team có đủ 6 slot
        while len(self.team) < 6:
            slot = len(self.team) + 1
            self.team.append({
                "slot": slot, "name": "", "types": [], "moves": []
            })

        self._build_ui()
        self._refresh_team_panel()
        self._load_pokemon_editor(0)

    # ---------- UI BUILD ----------

    def _build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # --- Left panel: Team list ---
        left = tk.Frame(self, bg="#181825", width=200)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        left.grid_propagate(False)

        tk.Label(left, text="🎮 Team 6 Pokemon", bg="#181825", fg="#cdd6f4",
                 font=("Segoe UI", 11, "bold")).pack(pady=(10, 4))

        self.team_listbox = tk.Listbox(left, bg="#313244", fg="#cdd6f4",
                                        selectbackground="#89b4fa", activestyle="none",
                                        font=("Segoe UI", 10), borderwidth=0,
                                        highlightthickness=0)
        self.team_listbox.pack(fill="both", expand=True, padx=6, pady=4)
        self.team_listbox.bind("<<ListboxSelect>>", self._on_team_select)

        btn_frame = tk.Frame(left, bg="#181825")
        btn_frame.pack(fill="x", padx=6, pady=4)
        tk.Button(btn_frame, text="💾 Save Team", command=self._save_team,
                  bg="#a6e3a1", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2").pack(fill="x", pady=2)
        tk.Button(btn_frame, text="🔄 Reset Slot", command=self._reset_slot,
                  bg="#f38ba8", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2").pack(fill="x", pady=2)

        # --- Right panel: Editor ---
        right = tk.Frame(self, bg="#1e1e2e")
        right.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        right.rowconfigure(3, weight=1)
        right.columnconfigure(0, weight=1)

        # Pokemon name row
        name_row = tk.Frame(right, bg="#1e1e2e")
        name_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tk.Label(name_row, text="Tên Pokemon:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left")
        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(name_row, textvariable=self.name_var,
                                   bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                                   font=("Segoe UI", 11), relief="flat", width=25)
        self.name_entry.pack(side="left", padx=6)

        # Types row
        types_row = tk.Frame(right, bg="#1e1e2e")
        types_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        tk.Label(types_row, text="Type (vd: psychic,fairy):", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left")
        self.types_var = tk.StringVar()
        tk.Entry(types_row, textvariable=self.types_var,
                 bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                 font=("Segoe UI", 11), relief="flat", width=30).pack(side="left", padx=6)

        # --- Image buttons ---
        img_row = tk.Frame(right, bg="#1e1e2e")
        img_row.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        tk.Button(img_row, text="📷 Load ảnh Team tổng",
                  command=self._load_team_image,
                  bg="#89dceb", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2", padx=8).pack(side="left", padx=(0, 6))

        tk.Button(img_row, text="⚔️ Load ảnh Fight (4 move)",
                  command=self._load_fight_image,
                  bg="#f9e2af", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2", padx=8).pack(side="left", padx=(0, 6))

        tk.Button(img_row, text="🔍 OCR Tên Pokemon",
                  command=self._ocr_name_only,
                  bg="#cba6f7", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2", padx=8).pack(side="left")

        # --- Move editor (JSON text) ---
        tk.Label(right, text="Moves JSON (4 move – sửa trực tiếp):",
                 bg="#1e1e2e", fg="#a6adc8", font=("Segoe UI", 9)).grid(
                 row=3, column=0, sticky="w")

        self.moves_text = scrolledtext.ScrolledText(
            right, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
            font=("Consolas", 10), relief="flat", height=18
        )
        self.moves_text.grid(row=4, column=0, sticky="nsew", pady=(2, 4))
        right.rowconfigure(4, weight=1)

        # Status bar
        self.status_var = tk.StringVar(value="Sẵn sàng.")
        tk.Label(right, textvariable=self.status_var, bg="#1e1e2e", fg="#6c7086",
                 font=("Segoe UI", 9), anchor="w").grid(row=5, column=0, sticky="ew")

    # ---------- Team panel ----------

    def _refresh_team_panel(self):
        self.team_listbox.delete(0, "end")
        for i, poke in enumerate(self.team):
            name = poke.get("name") or f"(Slot {i+1})"
            prefix = "▶" if i == self.current_pokemon_index else "  "
            self.team_listbox.insert("end", f"{prefix} Slot {i+1}: {name}")
        self.team_listbox.selection_clear(0, "end")
        self.team_listbox.selection_set(self.current_pokemon_index)

    def _on_team_select(self, event):
        sel = self.team_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx == self.current_pokemon_index:
            return
        self._commit_current()
        self._load_pokemon_editor(idx)

    def _load_pokemon_editor(self, idx: int):
        self.current_pokemon_index = idx
        poke = self.team[idx]
        self.name_var.set(poke.get("name", ""))
        self.types_var.set(",".join(poke.get("types", [])))
        moves = poke.get("moves", [])
        self.moves_text.delete("1.0", "end")
        self.moves_text.insert("1.0", json.dumps(moves, indent=2, ensure_ascii=False))
        self._refresh_team_panel()
        self.status_var.set(f"Đang chỉnh Slot {idx+1}.")

    def _commit_current(self):
        """Lưu dữ liệu từ editor vào self.team tại current index"""
        idx = self.current_pokemon_index
        self.team[idx]["name"] = normalize(self.name_var.get())
        self.team[idx]["types"] = [
            t.strip().lower()
            for t in self.types_var.get().split(",")
            if t.strip()
        ]
        try:
            moves_json = self.moves_text.get("1.0", "end").strip()
            if moves_json:
                self.team[idx]["moves"] = json.loads(moves_json)
        except json.JSONDecodeError:
            pass  # Giữ nguyên nếu JSON sai

    # ---------- Image OCR actions ----------

    def _load_team_image(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh team tổng quan",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if not path:
            return
        img = load_image_cv2(path)
        if img is None:
            messagebox.showerror("Lỗi", "Không load được ảnh!")
            return
        names = ocr_team_from_image(img, self.config_data)
        # Cập nhật tên vào team
        for i, name in enumerate(names):
            if name:
                self.team[i]["name"] = name
        self._refresh_team_panel()
        self._load_pokemon_editor(self.current_pokemon_index)
        self.status_var.set(f"OCR team xong: {names}")

    def _load_fight_image(self):
        path = filedialog.askopenfilename(
            title=f"Chọn ảnh panel Fight của Slot {self.current_pokemon_index+1}",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if not path:
            return
        img = load_image_cv2(path)
        if img is None:
            messagebox.showerror("Lỗi", "Không load được ảnh!")
            return
        moves = ocr_moves_from_fight_image(img, self.config_data)
        self.moves_text.delete("1.0", "end")
        self.moves_text.insert("1.0", json.dumps(moves, indent=2, ensure_ascii=False))
        self.status_var.set(
            f"OCR moves Slot {self.current_pokemon_index+1} xong. Kiểm tra và sửa nếu cần."
        )

    def _ocr_name_only(self):
        """Load ảnh bất kỳ và OCR tên Pokemon (dòng đầu tiên)"""
        path = filedialog.askopenfilename(
            title="Chọn ảnh để OCR tên Pokemon",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if not path:
            return
        img = load_image_cv2(path)
        if img is None:
            messagebox.showerror("Lỗi", "Không load được ảnh!")
            return
        text = ocr_single_line(img, self.config_data, psm=7)
        name = parse_move_name(text)
        if name:
            self.name_var.set(normalize(name))
            self.status_var.set(f"OCR tên: '{name}'")
        else:
            self.status_var.set("Không OCR được tên, hãy nhập thủ công.")

    # ---------- Save / Reset ----------

    def _save_team(self):
        self._commit_current()
        # Kiểm tra có slot nào còn trống không
        empty_slots = [i+1 for i, p in enumerate(self.team) if not p.get("name")]
        if empty_slots:
            ok = messagebox.askyesno(
                "Cảnh báo",
                f"Slot {empty_slots} chưa có tên Pokemon. Vẫn lưu?"
            )
            if not ok:
                return
        # Đánh lại slot index
        for i, p in enumerate(self.team):
            p["slot"] = i + 1
        save_team(self.team)
        self._refresh_team_panel()
        messagebox.showinfo("Đã lưu", f"Đã lưu team vào:\n{TEAM_PATH}")
        self.status_var.set(f"Đã lưu {TEAM_PATH}")

    def _reset_slot(self):
        idx = self.current_pokemon_index
        ok = messagebox.askyesno("Xác nhận", f"Reset Slot {idx+1}?")
        if not ok:
            return
        self.team[idx] = {"slot": idx+1, "name": "", "types": [], "moves": []}
        self._load_pokemon_editor(idx)
        self.status_var.set(f"Đã reset Slot {idx+1}.")


def run_team_builder():
    """Mở Team Builder trong window riêng (standalone mode)"""
    config = load_config()
    init_tesseract(config)
    window = tk.Tk()
    window.title("Team Builder – Menu 4")
    window.geometry("980x700")
    window.resizable(True, True)
    
    app = TeamBuilderApp(window, config)
    app.pack(fill="both", expand=True)
    window.mainloop()


def create_team_builder_widget(master, config):
    """Tạo Team Builder widget để embed vào tab"""
    init_tesseract(config)
    return TeamBuilderApp(master, config)


class CalibrateMoveROIApp(tk.Frame):
    """Tab để calibrate 4 move slot ROI bằng drag & drop"""
    def __init__(self, master, config):
        super().__init__(master, bg="#1e1e2e")
        self.config_data = config
        self.image_cv = None
        self.image_tk = None
        self.roi_list = list(config.get("roi", {}).get("move_slots", [
            [1252, 308, 237, 58],
            [1252, 386, 243, 55],
            [1254, 452, 242, 61],
            [1257, 522, 243, 65]
        ]))
        self.dragging_slot = None
        self.drag_start = None

        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # Top: Instructions
        top_frame = tk.Frame(self, bg="#1e1e2e")
        top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)

        tk.Label(top_frame, text="📋 Calibrate Move Slots ROI",
                bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 12, "bold")).pack(side="left")

        tk.Button(top_frame, text="📸 Load Screenshot", command=self._load_screenshot,
                 bg="#89dceb", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                 relief="flat", cursor="hand2", padx=8).pack(side="left", padx=(20, 0))

        tk.Button(top_frame, text="💾 Save ROI", command=self._save_roi,
                 bg="#a6e3a1", fg="#1e1e2e", font=("Segoe UI", 9, "bold"),
                 relief="flat", cursor="hand2", padx=8).pack(side="left", padx=6)

        # Main: Canvas + ROI info
        main_frame = tk.Frame(self, bg="#1e1e2e")
        main_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=8)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Canvas for image
        self.canvas = tk.Canvas(main_frame, bg="#313244", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Right: ROI info
        info_frame = tk.Frame(main_frame, bg="#181825", width=200)
        info_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        info_frame.grid_propagate(False)

        tk.Label(info_frame, text="Move Slots ROI", bg="#181825", fg="#cdd6f4",
                font=("Segoe UI", 11, "bold")).pack(pady=(10, 4))

        self.roi_text = tk.Text(info_frame, bg="#313244", fg="#cdd6f4",
                               font=("Consolas", 9), height=10, width=22,
                               relief="flat", highlightthickness=0)
        self.roi_text.pack(fill="both", expand=True, padx=6, pady=4)

        self.status_var = tk.StringVar(value="Load ảnh screenshot để bắt đầu.")
        tk.Label(info_frame, textvariable=self.status_var, bg="#181825", fg="#6c7086",
                font=("Segoe UI", 8), wraplength=180, justify="left").pack(padx=6, pady=4)

    def _load_screenshot(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh battle fight panel",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All", "*.*")]
        )
        if not path:
            return
        self.image_cv = load_image_cv2(path)
        if self.image_cv is None:
            messagebox.showerror("Lỗi", "Không load được ảnh!")
            return
        self._display_image()
        self.status_var.set("Nhấn + kéo để adjust ROI từng move slot")

    def _display_image(self):
        """Hiển thị ảnh + các hình chữ nhật ROI lên canvas"""
        if self.image_cv is None:
            return

        h, w = self.image_cv.shape[:2]
        # Scale để fit canvas
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w, canvas_h = 800, 600

        scale = min(canvas_w / w, canvas_h / h, 1.0)
        new_w = int(w * scale)
        new_h = int(h * scale)

        img_small = cv2.resize(self.image_cv, (new_w, new_h))
        img_bgr = img_small.copy()

        # Vẽ ROI rectangles
        for i, roi in enumerate(self.roi_list):
            x, y, roi_w, roi_h = roi
            x, y = int(x * scale), int(y * scale)
            roi_w, roi_h = int(roi_w * scale), int(roi_h * scale)
            color = (0, 255, 0) if i != self.dragging_slot else (0, 0, 255)
            cv2.rectangle(img_bgr, (x, y), (x + roi_w, y + roi_h), color, 2)
            cv2.putText(img_bgr, f"M{i+1}", (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, (0, 255, 0), 1)

        # Convert to PhotoImage
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        from PIL import Image as PILImage, ImageTk as PILImageTk
        pil_img = PILImage.fromarray(img_rgb)
        self.image_tk = PILImageTk.PhotoImage(pil_img)
        self.scale_factor = scale

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.image_tk, anchor="nw")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        self._update_roi_text()

    def _on_canvas_click(self, event):
        """Detect click trên ROI nào"""
        if self.image_cv is None:
            return
        x, y = event.x, event.y
        for i, roi in enumerate(self.roi_list):
            rx, ry, rw, rh = roi
            rx, ry = int(rx * self.scale_factor), int(ry * self.scale_factor)
            rw, rh = int(rw * self.scale_factor), int(rh * self.scale_factor)
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                self.dragging_slot = i
                self.drag_start = (x, y)
                break

    def _on_canvas_drag(self, event):
        """Drag ROI"""
        if self.dragging_slot is None or self.drag_start is None:
            return
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]

        # Update ROI position
        roi = self.roi_list[self.dragging_slot]
        roi[0] = int(roi[0] + dx / self.scale_factor)
        roi[1] = int(roi[1] + dy / self.scale_factor)

        self.drag_start = (event.x, event.y)
        self._display_image()

    def _on_canvas_release(self, event):
        """Stop dragging"""
        self.dragging_slot = None
        self.drag_start = None

    def _update_roi_text(self):
        """Update text widget với ROI data"""
        self.roi_text.delete("1.0", "end")
        for i, roi in enumerate(self.roi_list):
            self.roi_text.insert("end", f"Move {i+1}: {roi}\n")

    def _save_roi(self):
        """Lưu ROI vào tool_config.json"""
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            config = json.load(f)
        config.setdefault("roi", {})["move_slots"] = self.roi_list
        with CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("✓ Lưu thành công", f"ROI đã lưu vào:\n{CONFIG_PATH}")
        self.status_var.set("✓ Đã lưu ROI!")


def create_team_builder_widget(master, config):
    """Tạo Team Builder widget để embed vào tab"""
    init_tesseract(config)
    return TeamBuilderApp(master, config)


if __name__ == "__main__":
    run_team_builder()
