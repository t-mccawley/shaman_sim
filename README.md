# ShamanSim

Monte Carlo DpS simulator for the WoW Forever Shaman, focused on Enhancement
(melee plus spells). It runs every compatible combination of character,
encounter, rotation, and talent build (a *candidate*) and writes an HTML
report comparing them. It follows the same design as MageSim.

## Setup

```sh
uv sync
```

## Run

```sh
uv run shamansim                    # simulate and open the report
uv run shamansim --no-open          # just write results/shamansim_<timestamp>.html
uv run shamansim --refresh-talents  # re-download Wowhead talent data first
uv run shamansim spellbook          # write results/spellbook.csv (use --out - for stdout)
uv run shamansim stat-weights       # write results/stat_weights_results.html
```

## Configure (`configs/`)

| File | Exports | Notes |
|---|---|---|
| `character.py` | `CHARACTERS: list[Character]` | Sheet stats, including strength and agility, melee (attack power, crit, hit, weapon skill bonus) and spells (per-school power, crit, hit). Also the main-hand `Weapon`, water, and `talents_on_sheet`. |
| `encounters.py` | `ENCOUNTERS: list[Encounter]` | Type, duration, enemy count, health, armor, level delta, and `position` (behind or front; parry only from the front). Leveling encounters also set `drink_below_mana_pct`. |
| `rotations.py` | `ROTATIONS: list[Rotation]` | A function `(SimState) -> spell or None`, plus a `weapon_imbue` and optional `rank_overrides`. |
| `talents.py` | `TALENT_URLS: list[str]` | Links from https://www.wowhead.com/forever/talent-calc/shaman |
| `spellbook.py` | `SPELL_RANKS`, `IMBUE_RANKS` | In-game values per rank. Pre-filled from Wowhead for levels 1-60; mark each rank `confirmed_in_game_date` once checked. |
| `meta.py` | `META: MetaConfig` | Seed, iterations, tick size, peak-DpS warmup, and confidence level. |
| `stat_weights.py` | `STAT_WEIGHTS: StatWeightsConfig` | One character, encounter, and rotation (by display name) and one talent link for `shamansim stat-weights`, plus the step simulated for each stat and optional `iterations`. |

`talents_on_sheet` is the talent link that was active when you copied the
sheet. Its stat talents are removed and each candidate's are applied:
- Thundering Strikes (crit);
- Ancestral Knowledge (intellect and mana);
- Mental Dexterity (attack power from intellect);
- Mental Quickness (spell power from intellect).

### Candidates

Every combination whose rotation `encounter_type` matches the encounter is a
candidate. It is **invalid** (not simulated, listed with reasons) when:
- the talent build's required level differs from the character's level;
- the weapon imbue or a `rank_overrides` rank isn't learnable at the character's level;
- the rotation uses a spell the character can't have. For example Stormstrike
  without the talent, or any talent spell's rank requires level 40.

  This is detected from the rotation's source and a probe run. Checking
  `.known` counts as handling it.

Talent links must follow the calculator's rules: 5 points per row above a
talent, plus prerequisites. Links that break them are rejected rather than
silently truncated the way Wowhead does.

### Writing a rotation

```python
def enhancement(s: SimState) -> SpellChoice:
    sb = s.spells
    if sb.stormstrike.ready:
        return sb.stormstrike
    if s.target is not None and s.target.stormstruck and sb.earth_shock.ready:
        return sb.earth_shock
    if s.maelstrom_stacks == 5:
        return sb.lightning_bolt
    return None  # keep auto attacking
```

Melee auto attacks run on their own. Returning `None` waits a tick.

- Spell handles expose `known`, `ready`, `on_cooldown`, `cooldown_remaining`,
  `mana_cost`, `affordable`, `cast_time`, and `rank`.
- `SimState` exposes:
  - `time`, `mana`, `mana_pct`;
  - `target` (`health_pct`, `stormstruck`, `has_dot(...)`), `enemies`;
  - `maelstrom_stacks`, `flurry_charges`, `clearcasting`;
  - `fire_totem`, `fire_totem_remaining`.

If a pick is on cooldown, unaffordable, or Fire Nova has no fire totem, the
character waits one tick, and the lost time is reported as "blocked".

## Outputs

The report layout is the same as MageSim's:
- Total and peak DpS as `median (low - high)`, with a 90% bootstrap confidence
  interval of the median.
- One chart with Total (blue) and Peak (red) bars per candidate, with hover
  summaries. Click a bar to open its talents.
- The median cumulative-DpS time series.
- A sortable, filterable Candidate Legend: damage share by source, casts per
  run by rank, kills, drinking, and blocked time.
- An Invalid Candidates section.

### Stat weights

`shamansim stat-weights` estimates how much DpS one more point of each stat is
worth for the combination in `stat_weights.py`. It writes
`results/stat_weights_results.html`:
- a bar chart of DpS per point, and one of DpS per 1% for percent stats, each
  with a 90% CI;
- a table of equivalence points (EP): DpS per point divided by attack power's
  DpS per point. If 1 attack power adds 0.05 DpS and 1 intellect adds 0.10,
  intellect's EP is 2.0.

The weighted stats are attack power, strength, agility, spell power,
intellect, spirit, mp5, weapon skill, melee crit and hit, and spell crit and
hit.

How the estimate works:
- Each stat is raised by its step, and that copy runs the same iterations, with
  the same seeds, as the unmodified character. Most of the noise cancels.
- DpS per point is the mean of the paired differences divided by the step. It
  is a mean, not a median: damage past an enemy's remaining health is lost, so
  small changes often leave a run's DpS exactly unchanged.
- Larger steps reduce noise but average across caps such as hit.
- Against low-health enemies, values can change with the step size: extra
  damage pays off in jumps as hits start killing in fewer swings. Compare
  stats at steps worth about the same damage; strength's default of 25 equals
  attack power's 50.
- Strength, agility, and intellect mean gear points. The sheet's talents scale
  them. Strength and agility add attack power and melee crit (see Modeling),
  and intellect adds the mana, attack power, and spell power its talents grant.

## Modeling

**Strength and agility** (wowsims/sod):
- The sheet's attack power and melee crit already include them; the simulator
  re-derives both, so talents that scale strength or agility affect them.
- 1 strength = 2 attack power. Agility gives no attack power.
- Agility's melee crit depends on level: 0.0971% per point at 25, 0.0717% at 40,
  0.0600% at 50, 0.0508% at 60. Other levels are interpolated (agility per 1%
  crit is nearly linear in level), and levels below 25 are extrapolated. That is
  an estimate.

**Melee** (wowsims/classic):
- The Classic attack table: miss, dodge, parry from the front, and glancing
  blows (40% against +3, at 55-75% damage). Specials never glance and roll
  crit separately.
- Weapon skill suppresses hit and crit.
- Damage is the weapon roll + AP / 14 × weapon speed, reduced by armor:
  armor / (armor + 400 + 85 × level).
- Swings wait while casting. Flurry and Rage of the Farseer speed them up.

**Imbues** (values from Forever tooltips; procs from wowsims):
- Rockbiter adds attack power.
- Flametongue deals X / 100 × weapon speed Fire damage per hit.
- Frostbrand procs 9 times per minute.
- Windfury has a 20% chance per hit of 2 extra attacks with bonus attack
  power, with a 1.5 s internal cooldown.
- Elemental Weapons scales all of them.

**Spells**:
- Coefficients are calculated from the configured cast time, DoT duration, or
  totem attack interval, times a per-spell scale fitted to wowsims. There is
  no low-level penalty, as in the Forever client. Audit them with
  `shamansim spellbook`.
- The Shocks share one cooldown.
- Chain Lightning hits 3 targets, losing 30% per jump.
- Lava Burst deals +20% while Flame Shock is on the target.
- Fire Nova needs an active fire totem.
- Stormstrike empowers the next Lightning Bolt, Chain Lightning, or Earth Shock.
- Lightning Overload, Elemental Focus, Elemental Devastation, and Maelstrom
  Weapon are modeled.

**Estimates and gaps**:
- Maelstrom Weapon's proc rate isn't stated; ShamanSim uses 10 procs per
  minute (the Season of Discovery value).
- Searing Totem's attack interval and Flame Shock's tick count come from
  wowsims, not the tooltips.
- Intellect's effect on spell crit is not modeled.
- Not modeled: dual wield (not in Forever's ability list), stat totems (enter
  their buffs in the sheet), Lightning Shield, Nature's Swiftness, Water
  Shield, Mana Tide, damage taken, and movement.

## Sources

- Spells, talents, and imbues: WoW Forever data from Wowhead. The talent data
  snapshot is in `src/shamansim/data/`.
- Formulas: [wowsims/classic](https://github.com/wowsims/classic).

## Development

```sh
uv run pytest
uv run mypy
uv run ruff check && uv run ruff format --check
```
