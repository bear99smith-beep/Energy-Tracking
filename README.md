# Octopus Energy Dashboard

Personal electricity (Agile) + gas dashboard for iPad using:
- FastAPI
- Fly.io
- Octopus Energy API

## Setup
```bash
fly secrets set OCTOPUS_API_KEY=sk_live_xxx
fly secrets set ELEC_MPAN=xxxx
fly secrets set ELEC_SERIAL=xxxx
fly secrets set GAS_MPRN=xxxx
fly secrets set GAS_SERIAL=xxxx
fly secrets set GAS_UNIT_RATE=6.89
fly secrets set GAS_STANDING_CHARGE=27.47
