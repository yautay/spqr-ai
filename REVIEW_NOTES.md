# REVIEW_NOTES

## Scope

Analiza porownawcza:

- instrukcja: `docs/SPQR_4thEdition_Living_Rules_Draft_Oct2022.pdf` (tekst wyciagniety lokalnie przez `pdftotext`),
- runtime: `apps/api/src/legions_api/**`,
- testy: `apps/api/tests/**`,
- dane scenariuszy i tabel: `apps/api/src/legions_api/data/**`.

Zakres merytoryczny: rozdzialy `3.0` do `11.0` instrukcji, czyli sekwencja gry, liderzy, aktywacje i rozkazy, ruch, facing, ZOC, missile, shock, special units, rout/rally/depletion, withdrawal i victory.

## Executive Summary

Repozytorium nie realizuje obecnie zasad SPQR 4th Edition "dokladnie" ani nawet blisko pelnej zgodnosci z instrukcja. Implementacja jest poprawnym technicznie szkieletem uproszczonego silnika taktycznego, ale nie odwzorowuje ogromnej czesci zasad krytycznych dla SPQR.

Najwazniejszy wniosek:

- runtime implementuje glownie uproszczone: `movement`, `missile`, `shock`, podstawowe `rout`, proste `pursuit`, replay/save-load i AI na tym uproszczonym modelu,
- runtime nie implementuje systemu liderow i dowodzenia, ktory w SPQR jest centralnym mechanizmem gry,
- runtime nie implementuje facingu jako stanu jednostki, przez co nie da sie poprawnie odwzorowac front/flank/rear, reaction facing, line command, phalanx rules, manipular rules ani wielu szczegolow shock i movement,
- kilka plikow danych scenariuszy i tabel sprawia wrazenie obslugi zasad, ale w runtime w ogole nie jest uzywanych.

W efekcie aktualny stan nalezy traktowac jako "inspirowany SPQR" albo "uprostrzony prototype tactical engine", a nie implementacje zgodna z instrukcja SPQR 4th Edition.

## What Was Verified

Sprawdzilem:

- extraction i tresc rozdzialow `3.0`-`11.0` instrukcji,
- modele runtime: `GameState`, `Unit`, `RulesetDefinition`, `ScenarioMap`,
- resolvery: `movement.py`, `missile.py`, `shock.py`, `turn/sequence.py`,
- loader scenariusza i tabele,
- API i persistence payloads,
- test suite.

Stan testow:

- `pytest apps/api/tests` -> `133 passed`

To potwierdza tylko, ze kod jest wewnetrznie spojny z wlasnymi uproszczeniami. Nie potwierdza zgodnosci z instrukcja SPQR.

## High-Level Verdict By Rule Area

| Area | Verdict |
|---|---|
| 3.0 Sequence of Play | incorrect |
| 4.0 Leaders | missing |
| 5.0 Leader Activation and Orders | missing / incorrect |
| 6.0 Movement | partial |
| 7.0 Facing and ZOCs | incorrect |
| 8.0 Combat | partial / incorrect |
| 9.0 Special Combat Units | mostly missing |
| 10.0 Effects of Combat | mostly missing / incorrect |
| 11.0 Army Withdrawal and Victory | missing |

## Critical Findings

### 1. Brak systemu liderow i dowodzenia, mimo ze instrukcja opiera na nim cala gre

Instrukcja:

- `3.0`, `4.0`, `5.0`
- aktywacja liderow wg `Initiative`, `Individual Orders`, `Line Commands`, `Command Range`, `Momentum`, `Trump`, `Elite Commander`, `Finished`, `Bypassed`, `Trumped`, `OC/SC`, ograniczenia rzymskie/kartaginskie.

Dowody w kodzie:

- `apps/api/src/legions_api/core/model/game_state.py:35-49`
- `apps/api/src/legions_api/core/turn/sequence.py:23-74`
- `apps/api/src/legions_api/core/actions.py:11-44`
- `apps/api/src/legions_api/api/schemas.py:22-59`
- `apps/api/src/legions_api/persistence/state_codec.py:15-73`

Problem:

- runtime nie ma modelu `Leader`,
- nie ma `leader_id` w zadnej akcji,
- nie ma `command_range`, `initiative`, `line_command`, `strategy`, `charisma`, `elite_commander`,
- nie ma kolejnosci aktywacji liderow,
- nie ma systemu `Individual Orders` / `Line Commands`,
- nie ma `Momentum`, `Trump`, `Trump-the-Trump`, `Momentum Trump`,
- nie ma stanow liderow `inactive/active/finished/bypassed/trumped`.

Wniosek:

- To nie jest detal. To eliminuje glowny silnik reguł SPQR.

### 2. Sekwencja tury jest niezgodna z instrukcja

Instrukcja:

- `3.0`: aktywujesz lidera, robisz jego Orders, Shock, ewentualny Momentum, potem kolejnego lidera; dopiero po wszystkich liderach jest `Rout and Reload`, a potem `Withdrawal`.

Dowody w kodzie:

- `apps/api/src/legions_api/core/turn/sequence.py:23-42`
- `apps/api/tests/test_turn_sequence.py:9-58`

Problem:

- runtime ma tylko prosty cykl: `ORDERS -> SHOCK -> ROUT_AND_RELOAD -> change side`,
- nie ma wielokrotnych aktywacji liderow w ramach strony,
- `Rout and Reload` dzieje sie po kazdym takim cyklu, a nie po wszystkich liderach,
- `Withdrawal Phase` nie istnieje w runtime.

Wniosek:

- Silnik faz jest architektonicznie zbudowany pod inna gre niz SPQR.

### 3. Facing nie istnieje w runtime, mimo ze instrukcja stale sie na nim opiera

Instrukcja:

- `6.0`, `7.0`, `8.0`, `9.0`
- front/flank/rear, reaction facing, line orientation, phalanx behavior, manipular extension, movement entry through front, shock angle.

Dowody w kodzie:

- scenariusz ma `facing`: `apps/api/src/legions_api/data/scenarios/demo/order_of_battle.json:17-19,37-39`
- loader ignoruje `facing`: `apps/api/src/legions_api/core/scenario/loader.py:74-99`
- model `Unit` nie ma pola `facing`: `apps/api/src/legions_api/core/model/unit.py:27-44`
- `ShockAction` przyjmuje `angle` z payloadu: `apps/api/src/legions_api/core/actions.py:38-44`

Problem:

- kat shocku jest podawany recznie przez klienta zamiast byc wyliczany ze stanu gry,
- ZOC jest 360 stopni,
- nie da sie poprawnie wdrozyc:
  - front-only movement,
  - front/flank/rear superiority,
  - reaction facing,
  - same orientation in line,
  - phalanx defense,
  - Roman manipular rules.

Wniosek:

- Bez facingu pelna zgodnosc z instrukcja jest niemozliwa.

### 4. ZOC jest uproszczone i merytorycznie niezgodne z instrukcja

Instrukcja:

- `7.21`-`7.25`
- ZOC zalezy od facingu, typu jednostki i stanu; wejscie do ZOC zatrzymuje ruch; wyjscie ma szczegolne warunki; sa wyjatki.

Dowody w kodzie:

- `apps/api/src/legions_api/core/rules/zoc.py:10-28`
- `apps/api/src/legions_api/core/rules/movement.py:183-208`

Problem:

- ZOC obejmuje wszystkie 6 sasiednich hexow,
- brak frontowych ZOC,
- brak wyjatkow zaleznych od typu i facingu,
- brak szczegolowych zasad opuszczania ZOC,
- ruch jest po prostu blokowany, jesli `zoc_locks_movement` i jednostka stoi w enemy ZOC.

Wniosek:

- To nie jest implementacja zasad SPQR ZOC, tylko prosty pin mechanic.

### 5. Shock combat jest tylko uproszczonym 1v1 resolverem, a nie pelna procedura SPQR

Instrukcja:

- `8.41`-`8.47`, `8.5`, `8.6`
- shock designation, pre-shock TQ, leader casualties, clash, superiority, size ratio, terrain/angle/facing effects, collapse/rout, advance after combat, cavalry pursuit.

Dowody w kodzie:

- `apps/api/src/legions_api/core/rules/shock.py:38-457`
- `apps/api/tests/test_shock.py:19-269`

Co jest:

- baza CRT,
- clash columns,
- superiority lookup,
- rzut deterministyczny,
- dodanie cohesion hits,
- prosty morale check,
- prosty retreat,
- prosty pursuit.

Czego brakuje lub jest bledne:

- brak globalnego segmentu shock z wieloma starciami,
- brak `shock designation` i `SHOCK MUST CHECK TQ`,
- brak `pre-shock TQ checks`,
- brak `leader casualty` resolution,
- brak automatycznego wyliczania kata z facingu,
- brak wykorzystania `size` z jednostek,
- brak size ratio,
- brak wielu modyfikatorow terenowych/sytuacyjnych,
- brak `attack all units in ZOC` / `defender shocked once` semantics,
- brak `advance after combat`,
- pursuit jest sprowadzone do wejscia w opuszczony hex.

Wniosek:

- To jest tylko czesc matematycznego rdzenia CRT, nie zasady shock combat SPQR.

### 6. Rout, rally, depletion i withdrawal sa w duzej czesci niezaimplementowane albo niepoprawne

Instrukcja:

- `10.0`, `11.0`

Dowody w kodzie:

- `apps/api/src/legions_api/core/rules/shock.py:290-434`
- `apps/api/src/legions_api/core/rules/missile.py:153-207`
- `apps/api/src/legions_api/core/model/unit.py:27-125`
- `apps/api/src/legions_api/data/tables/rally_table.json`
- `apps/api/src/legions_api/data/scenarios/demo/victory.json:1-19`

Problem:

- rout nie uzywa `retreat_edges`,
- rout movement nie jest realizowany jak w instrukcji,
- routed units nadal moga byc aktywnie poruszane/strzelac/shockowac,
- `rally` nie istnieje jako akcja runtime,
- `rally_table` istnieje, ale jest martwa,
- `depletion` nie istnieje jako osobny stan,
- `depleted` w loaderze jest mylnie mapowane na `MissileSupply.NO`,
- `withdrawal` i `rout points` nie istnieja w runtime.

Wniosek:

- Koncowka tury i system morale armii sa niezaimplementowane.

## Detailed Comparison By Rule Chapter

### 3.0 Sequence of Play

Status: `incorrect`

Zgodne czesci:

- istnieja trzy fazy runtime: `orders`, `shock`, `rout_and_reload`.

Niezgodnosci:

- brak aktywacji liderow wg `Initiative`,
- brak `Momentum Phase`,
- brak `Trump`,
- brak `Withdrawal Phase`,
- `Rout and Reload` jest w runtime umieszczone zla granularnoscia.

Referencje:

- `apps/api/src/legions_api/core/model/game_state.py:17-23`
- `apps/api/src/legions_api/core/turn/sequence.py:23-74`

### 4.0 Leaders

Status: `missing`

Niezgodnosci:

- brak modelu liderow,
- brak command range,
- brak command restrictions,
- brak OC/SC special powers,
- brak leader casualties,
- brak replacement leaders,
- brak leader elephants.

Szczegolnie istotne:

- szablon scenariusza przewiduje liderow, ale loader ich nie laduje:
  - `apps/api/src/legions_api/data/scenarios/_template/order_of_battle.template.json:6-18`
  - `apps/api/src/legions_api/core/scenario/loader.py:74-99`

### 5.0 Leader Activation and Orders

Status: `missing / incorrect`

Niezgodnosci:

- brak `Individual Orders` jako budzetu wydanego przez konkretnego lidera,
- brak `Line Commands`,
- brak `Finished`, `Bypassed`, `Trumped`,
- brak `Momentum`,
- brak `Elite Commander Initiative`.

Pozor implementacji:

- endpoint `/game/activation/advance` sugeruje mechanike aktywacji,
- w praktyce przesuwa tylko globalna faze bez wyboru lidera.

Referencje:

- `apps/api/src/legions_api/api/routes/game.py:239-260`
- `apps/api/src/legions_api/core/turn/sequence.py:23-74`

### 6.0 Movement

Status: `partial`

Zaimplementowane:

- pathfinding,
- koszty ruchu przez teren,
- passability,
- occupancy/stacking bazowe,
- podstawowe reaction windows pod missile fire,
- deterministyczne TQ checks dla stacking side effects.

Braki lub bledy:

- brak ruchu zaleznego od facingu,
- brak wielokrotnego ruchu w turze z CH,
- brak `one move per Orders Phase`,
- brak `Orderly Withdrawal`,
- brak `pre-arranged withdrawal`,
- brak `column movement`,
- brak phalanx maneuvers,
- brak poprawnej integracji terrain/elevation CH z instrukcji,
- brak ruchu liderow.

Referencje:

- `apps/api/src/legions_api/core/rules/movement.py:81-532`
- `apps/api/tests/test_movement.py:19-829`

### 7.0 Facing and ZOCs

Status: `incorrect`

Najwieksze problemy:

- facing nie istnieje w runtime,
- ZOC jest 6-kierunkowe,
- shock angle podaje klient,
- brak reaction facing,
- brak warunkow `must shock` i `attack all in ZOC`.

Referencje:

- `apps/api/src/legions_api/core/model/unit.py:27-44`
- `apps/api/src/legions_api/core/rules/zoc.py:10-28`
- `apps/api/src/legions_api/core/actions.py:38-44`

### 8.0 Combat

Status: `partial / incorrect`

Missile:

- plusy:
  - range table,
  - LOS,
  - DR modifiers,
  - ammo state,
  - reaction fire skeleton.
- braki:
  - brak `once per Orders Phase`,
  - brak poprawnych warunkow reload z instrukcji,
  - brak `H&D`,
  - brak wielu szczegolowych triggerow reaction/return fire,
  - brak stack-top/bottom constraints,
  - brak special elephant/screen/scorpio treatment.

Shock:

- plusy:
  - clash columns,
  - superiority chart,
  - CRT.
- braki:
  - brak pre-shock checks,
  - brak leader casualty,
  - brak size ratio,
  - brak correct collapse/rout flow,
  - brak advance after combat,
  - pursuit za bardzo uproszczony.

Referencje:

- `apps/api/src/legions_api/core/rules/missile.py:30-354`
- `apps/api/src/legions_api/core/rules/shock.py:38-457`

### 9.0 Special Combat Units

Status: `mostly missing`

Braki:

- elephants: pass-thru, rampage, cavalry interaction, Indian vs African,
- skirmishers: shock restrictions i rout elimination,
- phalanx defense,
- double-depth phalanx,
- manipular line extension,
- triarii doctrine,
- scorpio/artillery.

Pozory implementacji:

- `special_rules.json` istnieje,
- `unit_type_traits.json` istnieje,
- ale runtime prawie w ogole z nich nie korzysta.

Referencje:

- `apps/api/src/legions_api/data/scenarios/demo/special_rules.json:1-13`
- `apps/api/src/legions_api/data/tables/unit_type_traits.json`
- `apps/api/src/legions_api/core/scenario/loader.py:17-24,50-53,74-99`

### 10.0 The Effects of Combat

Status: `mostly missing / incorrect`

Braki lub bledy:

- brak auto-rout przy `hits >= TQ`,
- brak full rout movement,
- brak proper routed restrictions,
- brak rally action,
- brak depletion state,
- engaged optional rule nie istnieje w runtime,
- `cohesion_tq_checks.json` praktycznie martwe.

Referencje:

- `apps/api/src/legions_api/core/rules/shock.py:290-434`
- `apps/api/src/legions_api/core/model/unit.py:85-125`
- `apps/api/src/legions_api/data/tables/rally_table.json`
- `apps/api/src/legions_api/data/tables/cohesion_tq_checks.json`

### 11.0 Army Withdrawal and Victory

Status: `missing`

Braki:

- brak liczenia `Rout Points`,
- brak `Withdrawal Level` checks,
- brak tie resolution,
- brak `retreat_edges` runtime.

Pozor implementacji:

- `victory.json` istnieje,
- loader wymaga jego obecnosci,
- runtime go nie laduje i nie uzywa.

Referencje:

- `apps/api/src/legions_api/data/scenarios/demo/victory.json:1-19`
- `apps/api/src/legions_api/core/scenario/loader.py:17-24,46-52`

## Dead Data And False Sense Of Coverage

To sa miejsca, ktore wygladaja na zaimplementowane, ale runtime z nich nie korzysta albo korzysta minimalnie:

1. `apps/api/src/legions_api/data/scenarios/demo/line_command_eligibility.json`
   Runtime nigdzie tego nie parsuje ani nie wykorzystuje do `Line Commands`.

2. `apps/api/src/legions_api/data/scenarios/demo/special_rules.json`
   Plik jest wymagany przez loader, ale nie jest ladowany do `GameState`.

3. `apps/api/src/legions_api/data/scenarios/demo/victory.json`
   Plik jest wymagany, ale withdrawal/victory logic nie istnieje.

4. `apps/api/src/legions_api/data/tables/rally_table.json`
   Jest model i loader, ale brak `RallyAction` i resolvera.

5. `apps/api/src/legions_api/data/tables/leader_casualty_table.json`
   Jest model i loader, ale brak runtime consumer w `shock.py` i `missile.py`.

6. `apps/api/src/legions_api/data/tables/cohesion_tq_checks.json`
   Instrukcyjnie bardzo wazne, ale w runtime prawie nieuzywane.

7. `apps/api/src/legions_api/data/scenarios/_template/order_of_battle.template.json`
   Szablon zawiera liderow i ich ratingi, ale prawdziwy loader laduje tylko jednostki.

## Concrete Rule Mismatches Worth Fixing First

### Rules implemented incorrectly

1. `Turn sequence`
   Kod nie realizuje leader-driven turn order.

2. `Facing`
   Jest w danych scenariusza, ale nie ma go w runtime.

3. `ZOC`
   Jest 360 stopni zamiast zgodnego z facing/front.

4. `Shock angle`
   Pochodzi z payloadu klienta, zamiast byc wyliczony z planszy.

5. `Routed unit behavior`
   Routed unit nie jest wystarczajaco ograniczona.

6. `Depletion`
   Zostalo pomylone z `missile_supply`.

7. `Reload`
   Warunki i rezultat sa niezgodne z instrukcja `8.18`.

8. `Pursuit`
   Zbyt uproszczone, bez tabeli i decyzji/ograniczen z instrukcji.

### Rules completely missing

1. `Leaders`
2. `Command range`
3. `Individual Orders`
4. `Line Commands`
5. `Momentum`
6. `Trump`
7. `Elite Commander`
8. `Orderly Withdrawal`
9. `Reaction Facing`
10. `H&D`
11. `Pre-shock TQ`
12. `Leader casualty`
13. `Advance after combat`
14. `Rally`
15. `Withdrawal and victory`
16. `Elephants special rules`
17. `Phalanx special rules`
18. `Manipular Line Extension`
19. `Triarii doctrine`
20. `Scorpio artillery`

## Architecture Review

## Overall Assessment

Architektura warstwowa jako ogolny kierunek jest sensowna:

- `core/` oddzielone od FastAPI,
- `api/` jako transport,
- `persistence/` osobno,
- dane tabelaryczne sa poza kodem.

Natomiast aktualna architektura nie jest jeszcze poprawnie dostrojona do zlozonosci zasad SPQR. W szczegolnosci model domeny jest za plytki i przez to spora czesc danych istnieje tylko jako dekoracja wokol uproszczonego runtime.

## Architectural Problems

### 1. Model domeny jest zbyt ubogi dla tej gry

`Unit` i `GameState` nie niosa danych potrzebnych do poprawnego odwzorowania instrukcji.

Brakuje co najmniej:

- facing,
- size,
- leader collection i leader state,
- command metadata,
- moved/fired/shocked markers per phase/turn,
- depletion state,
- engaged state,
- scenario victory state,
- retreat edge metadata in runtime,
- line command eligibility runtime structures,
- scenario special rules runtime structures.

Referencje:

- `apps/api/src/legions_api/core/model/unit.py:27-44`
- `apps/api/src/legions_api/core/model/game_state.py:35-49`

### 2. Scenario loader tworzy pozor bogatego scenariusza, ale laduje tylko mala czesc danych

Problem:

- loader wymaga pieciu plikow scenariusza,
- faktycznie wczytuje tylko `map.json` i `order_of_battle.json`,
- nawet z `order_of_battle.json` ignoruje liderow, `size`, `facing` i inne pola.

Referencje:

- `apps/api/src/legions_api/core/scenario/loader.py:17-24,39-105`

To powinno zostac rozbite na jawne typed loaders:

- `load_map()`,
- `load_order_of_battle()`,
- `load_leaders()`,
- `load_line_command_rules()`,
- `load_special_rules()`,
- `load_victory_rules()`.

### 3. Zbyt duza odpowiedzialnosc spoczywa na kilku duzych plikach

Najwieksze pliki:

- `apps/api/src/legions_api/api/routes/game.py` -> `579` linii,
- `apps/api/src/legions_api/core/rules/movement.py` -> `532` linii,
- `apps/api/src/legions_api/core/rules/shock.py` -> `457` linii,
- `apps/api/src/legions_api/core/rules/missile.py` -> `354` linii,
- `apps/api/tests/test_movement.py` -> `829` linii.

To nie jest katastrofa samo w sobie, ale widac objawy mieszania odpowiedzialnosci.

Szczegolnie do rozbicia:

1. `api/routes/game.py`
   Rozdzielic na:
   - `routes/setup.py`
   - `routes/actions.py`
   - `routes/replay.py`
   - `routes/snapshots.py`
   - `routes/reference.py`

2. `core/rules/movement.py`
   Rozdzielic na:
   - `movement/validation.py`
   - `movement/resolution.py`
   - `movement/reaction_fire_windows.py`
   - `movement/stacking.py`
   - `movement/tq_checks.py`

3. `core/rules/shock.py`
   Rozdzielic na:
   - `shock/validation.py`
   - `shock/columns.py`
   - `shock/crt.py`
   - `shock/pre_shock.py`
   - `shock/rout.py`
   - `shock/pursuit.py`
   - docelowo `shock/advance.py`, `shock/leader_casualties.py`

4. `core/rules/missile.py`
   Rozdzielic na:
   - `missile/validation.py`
   - `missile/resolution.py`
   - `missile/reaction.py`
   - `missile/reload.py`
   - `missile/hit_and_disengage.py`

### 4. Runtime jest za mocno zbudowany wokol "akcja jednostki", a za slabo wokol "procedura fazy"

SPQR wymaga nie tylko walidacji pojedynczej akcji, ale tez proceduralnego segmentu gry:

- aktywacja lidera,
- wydawanie rozkazow z budzetem,
- designation step,
- resolve-many-combats-in-order step,
- end-of-activation consequences,
- end-of-turn routing and withdrawal.

Obecny model:

- `POST move`, `POST missile`, `POST shock`, `POST reload`

jest za plaski dla zasad tej gry.

Potrzebny bylby jawny orchestration layer, np.:

- `core/turn/activation_engine.py`
- `core/turn/orders_context.py`
- `core/turn/shock_segment.py`
- `core/turn/rout_reload_segment.py`
- `core/turn/withdrawal_segment.py`

### 5. Table-driven design jest dobra, ale jest niespojna z runtime

Plusem jest istnienie typed tables i loadera.

Minusem jest to, ze:

- niektore tabele sa uzywane,
- inne tylko istnieja,
- czesc kluczowych zasad jest nadal zaszyta lub pomijana w kodzie,
- `movement_costs` model przewiduje facing/elevation/cohesion details, ale runtime z nich nie korzysta w pelni.

To tworzy duzy rozdzwiek miedzy "data model says yes" a "runtime says maybe/no".

## Recommended Refactoring Direction

### 1. Najpierw naprawic model domeny

Minimalny konieczny krok:

- dodac `Facing` do `Unit`,
- dodac `size` do `Unit`,
- dodac `Leader` i `LeaderState`,
- dodac `ScenarioRules` do `GameState`,
- dodac per-turn/per-phase markers.

Bez tego dalsze dopisywanie zasad bedzie prowizorka.

### 2. Przebudowac sekwencje tury pod liderow

Najwazniejsza funkcjonalna przebudowa:

- obecny `advance_activation_step()` trzeba zastapic prawdziwym `activation engine`,
- fazy musza byc osadzone w aktywacji lidera,
- `Momentum`, `Trump`, `Finished`, `Bypassed`, `Elite` musza byc czescia stanu.

### 3. Wczytywac wszystkie dane scenariusza do runtime albo przestac wymagac martwych plikow

Obecna sytuacja jest mylaca.

Albo:

- loader ma realnie ladowac `victory.json`, `special_rules.json`, `line_command_eligibility.json`,

albo:

- nie powinien ich wymagac do `available_scenarios()` i `load_scenario_state()`.

### 4. Odrzucic angle z payloadu klienta

`ShockAction.angle` nie powinien byc zrodlem prawdy.

Powinno byc:

- klient wskazuje attacker + defender,
- silnik sam liczy angle z facing/pozycji.

### 5. Rozdzielic "coverage of tests" od "coverage of rules"

Aktualne testy sa dobre dla obecnego kodu, ale sprawdzaja glownie uproszczony behavior.

Powinny dojsc testy typu:

- one rule paragraph -> one focused rule test,
- end-to-end activation tests,
- scenario snippets from actual rulebook situations,
- tests for dead-data prevention: jesli plik scenariusza jest wymagany, musi miec runtime consumer.

## Priority Fix List

### P0: Fundamental blockers

1. Dodac leaders do runtime.
2. Dodac facing do runtime.
3. Przebudowac turn sequence pod activations.
4. Wczytac `size`, `victory`, `special_rules`, `line_command_eligibility`.

### P1: Core rules correctness

1. Command range / IO / LC.
2. Momentum / Trump / Elite Commander.
3. Proper ZOC and shock eligibility.
4. Pre-shock, leader casualties, size ratio.
5. Rout/rally/depletion.
6. Withdrawal/victory.

### P2: System-specific depth

1. Orderly Withdrawal.
2. H&D.
3. Advance after combat.
4. Full pursuit system.
5. Elephants.
6. Phalanx and double-depth phalanx.
7. Manipular line extension.
8. Triarii doctrine.
9. Scorpio artillery.

## Update 2026-04-05

The repo has moved materially beyond the original verdict above, but the verdict still stands for full rulebook parity.

What is now implemented beyond the earlier review snapshot:

- leaders and leader-driven activation baseline,
- scenario loading for `victory`, `special_rules`, and `line_command_eligibility`,
- vertex-based facing stored in runtime state,
- front-only ZOC for standard units,
- shock angle resolved from geometry rather than trusted client payload,
- explicit wide-unit footprint model with `position_b`,
- footprint-aware occupancy, ZOC, shock adjacency, and shock angle,
- basic wide-unit movement support for straight-ahead translation and reverse-face validation path.

What remains materially incomplete from the review perspective:

- full phalanx maneuvers (`front-to-flank`, wheeling, exact reverse-face restrictions/costs),
- column rules,
- orderly withdrawal and pre-arranged withdrawal,
- complete missile/LOS footprint handling for wide units,
- full shock sequence depth (pre-shock, leaders, size ratio, exact advance-after-combat handling),
- full special-units package,
- rout/rally/depletion/withdrawal/victory closure.

## Final Verdict

Jesli pytanie brzmi:

- "czy repozytorium dokladnie realizuje to, jak instrukcja SPQR formuluje zasady gry?"

odpowiedz brzmi:

- `nie`.

Jesli pytanie brzmi:

- "czy to jest sensowny fundament techniczny pod przyszla implementacje SPQR?"

odpowiedz brzmi:

- `tak, ale tylko jako fundament`,
- obecny model domeny i sekwencja tury wymagaja powaznej przebudowy, zanim da sie uczciwie mowic o zgodnosci z instrukcja.
