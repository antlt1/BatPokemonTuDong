"""
ocr_utils.py — Shared OCR utilities for the entire project.
Gom tất cả preprocessing, OCR text, fuzzy matching, move/Pokemon lookup tables.
"""

import difflib
import re
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

# ── Whitelist Tesseract cho OCR tên Pokemon ──
TESS_NAME_CFG = "--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- "

# ── Pokemon names Gen 1-9 (for fuzzy match) ──
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

# ── Move data (type / power / accuracy) ──
KNOWN_MOVES: dict = {}

_KNOWN_MOVES_INLINE = [
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

_POKEMON_NAMES_LOWER = [n.lower() for n in POKEMON_NAMES]
_KNOWN_MOVES_LOWER = {k.lower(): v for k, v in KNOWN_MOVES.items()}


# ══════════════════════════════════════════════════════════════
#  Text helpers
# ══════════════════════════════════════════════════════════════

def normalize_text(value: str) -> str:
    """Chuẩn hóa text: lowercase, collapse spaces, strip."""
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_move_name(text: str) -> str:
    """Làm sạch tên move từ OCR output."""
    cleaned = re.sub(r"[^A-Za-z0-9 '\-]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\b(pp|type|power|acc)\b", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def parse_pp(text: str):
    """Trích PP từ chuỗi kiểu '14/15' hoặc '14 15' → (14, 15)."""
    m = re.search(r"(\d+)\s*[/\|\\lI\s]\s*(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def fuzzy_fix_name(name: str, known_names: list = None) -> str:
    """Fuzzy match tên Pokemon với danh sách đã biết."""
    if not name:
        return ""
    if known_names is None:
        known_names = POKEMON_NAMES
    clean_name = re.sub(r"[^a-z\s]", "", normalize_text(name)).strip()
    matches = difflib.get_close_matches(clean_name, [n.lower() for n in known_names],
                                        n=1, cutoff=0.45)
    if matches:
        idx = [n.lower() for n in known_names].index(matches[0])
        return known_names[idx].lower()
    words = clean_name.split()
    for w in words:
        if len(w) >= 3:
            m = difflib.get_close_matches(w, [n.lower() for n in known_names],
                                          n=1, cutoff=0.7)
            if m:
                idx = [n.lower() for n in known_names].index(m[0])
                return known_names[idx].lower()
    return words[0][:15] if words else name


def get_known_pokemon_names(targets_path: Path = None, team_path: Path = None) -> list:
    """Gộp POKEMON_NAMES với tên từ target/team JSON."""
    import json
    names = set(POKEMON_NAMES)
    for path in [targets_path, team_path]:
        if path and path.exists():
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(data, list):
                    for item in data:
                        n = item.get('pokemonname') or item.get('name')
                        if n:
                            names.add(n)
            except Exception:
                pass
    return sorted(names)


# ══════════════════════════════════════════════════════════════
#  Image / OCR helpers
# ══════════════════════════════════════════════════════════════

def set_tesseract_path(config: dict):
    """Set Tesseract executable path từ config nếu có."""
    cmd = config.get("ocr", {}).get("tesseract_cmd", "").strip()
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


def preprocess_for_ocr(image_bgr, scale=3):
    """Preprocess ảnh BGR sang grayscale threshold cho OCR."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def ocr_text(image_bgr, config, psm=6) -> str:
    """OCR 1 vùng ảnh BGR, trả về text."""
    processed = preprocess_for_ocr(image_bgr)
    pil_image = Image.fromarray(processed)
    lang = config.get("ocr", {}).get("language", "eng")
    return pytesseract.image_to_string(
        pil_image,
        lang=lang,
        config=f"--psm {psm}",
    ).strip()


def ocr_text_variants(image_bgr, config, psm=6) -> str:
    """OCR với nhiều variant threshold, chọn kết quả nhiều chữ cái nhất."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    big = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    variants = [
        big,
        cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        cv2.threshold(big, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
    ]
    results = []
    for variant in variants:
        try:
            text = pytesseract.image_to_string(
                Image.fromarray(variant),
                lang=config.get("ocr", {}).get("language", "eng"),
                config=f"--psm {psm}",
            ).strip()
            if text:
                results.append(text)
        except Exception:
            continue
    if not results:
        return ""
    return max(results, key=len)


def ocr_variants(img_bgr, config, psm=7, name_mode=False) -> str:
    """
    Thử nhiều cách preprocess, trả về kết quả OCR hợp lệ nhất.
    name_mode=True: dùng whitelist chỉ chữ cái (tốt cho OCR tên Pokemon).
    """
    lang = config.get("ocr", {}).get("language", "eng")
    tess_cfg = TESS_NAME_CFG if name_mode else f"--psm {psm} --oem 3"
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    big = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    variants = [
        cv2.threshold(big, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
        cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        cv2.threshold(big, 180, 255, cv2.THRESH_BINARY)[1],
        cv2.threshold(big, 80, 255, cv2.THRESH_BINARY_INV)[1],
        big,
    ]

    best = ""
    for v in variants:
        txt = pytesseract.image_to_string(Image.fromarray(v), lang=lang, config=tess_cfg).strip()
        letters_txt = sum(c.isalpha() for c in txt)
        letters_best = sum(c.isalpha() for c in best)
        if letters_txt > letters_best:
            best = txt
    return best


def guess_move_data(name: str) -> dict:
    """Tra cứu move data từ KNOWN_MOVES. Fallback normal/0/100."""
    key = normalize_text(name)
    if key in KNOWN_MOVES:
        return dict(KNOWN_MOVES[key])
    for k, v in KNOWN_MOVES.items():
        if key in k or k in key:
            return dict(v)
    return {"type": "normal", "power": 0, "accuracy": 100}


def extract_pokemon_name_from_ocr(text: str) -> str:
    """Trích tên Pokemon từ chuỗi OCR."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines:
        cleaned = re.sub(r'\bLv\.?\s*\d+\b', '', line, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^A-Za-z\s\-']", '', cleaned).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        noise_words = {'lv', 'hp', 'pp', 'ok', 'no', 'is', 'the', 'and'}
        if len(cleaned) >= 3 and cleaned.lower() not in noise_words:
            return cleaned
    return ''


def fuzzy_match_pokemon(raw: str) -> str:
    """Fuzzy match tên Pokemon với POKEMON_NAMES."""
    if not raw or len(raw) < 3:
        return raw
    raw_lower = raw.lower()
    matches = difflib.get_close_matches(raw_lower, _POKEMON_NAMES_LOWER, n=1, cutoff=0.55)
    if matches:
        idx = _POKEMON_NAMES_LOWER.index(matches[0])
        return POKEMON_NAMES[idx]
    return raw


def crop_roi(image, roi):
    """Crop vùng ROI từ ảnh: roi = [x, y, w, h]."""
    x, y, w, h = roi
    return image[y:y+h, x:x+w]


def load_image_cv2(path: str):
    """Load ảnh bằng OpenCV (hỗ trợ Unicode path)."""
    import numpy as np
    arr = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)
