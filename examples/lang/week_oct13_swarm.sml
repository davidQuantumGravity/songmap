# The Swarm (2:03): the v0.2 port (examples/v0.2_yaml/week_oct13_swarm.songmap.yaml) in the
# SongMap language. Same notes, same digest (tests/test_lang.py).
song "Week of Oct 13 — The Swarm" 120 4/4 Em fps=30 seed=7 mood=techno tail=3 video=WeekSwarm:3690
inst bass(cutoff=700)
chords Em C G D /2
master legacy
motif m1 deg oct=5 "0 -3 0 2 | 1/2 0"
motif m2 deg oct=5 "-2 -3 -2 0 | -1/2. -3/4"
motif m3 deg oct=5 "2 0 2 4 | 3/2 2"
motif m4 deg oct=5 "1/4. 0/8 -1/2 | -3/1"

# this song's 12-step arp order, shared by both arp colours
order = [0, 2, 1, 3, 0, 2, 4, 3, 1, 2, 0, 3]
up = up(order=order)
dim = dark(order=order)
lift = !impact !riser:2 !riser:1@+8

terminal = {arp: dim, fx: ticks, bass: sub}
swarm_in = terminal with {drums: four_floor, bass: eighths}
goals = {drums: full+fill, bass: eighths, arp: up, pad: warm}
who = {pad: dark, fx: ticks}
agents = goals with {lead: [m1, m2, m3, m4]}
agents.drums += open
so_what = terminal with {pad: warm}
output = agents with {fx: ticks}
output.drums += hats16
guardrails = so_what with {fx: none}
summary = {pad: warm, arp: up}
end_card = {pad: dark}

form:
  terminal 4
  swarm_in 4    !impact
  goals 8       !riser:1
  who 2
  agents 16     !lift
  so_what 2
  output 16     !lift
  guardrails 4
  summary 2     !impact
  end_card 2    !impact
