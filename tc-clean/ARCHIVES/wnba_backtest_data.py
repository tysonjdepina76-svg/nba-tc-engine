"""Hardcoded WNBA backtest data for LV@GS"""
from datetime import datetime

WNBA_LV_GS_BACKTEST = {
    "date": "05/31",
    "away": "LV",
    "home": "GS",
    "sport": "WNBA",
    "tc_combined": 315.8,
    "signal": "UNDER",
    "lv_total": 179.1,
    "gs_total": 136.7,
    "players": {
        "LV": {
            "A'ja Wilson":       {"pos":"C","tc_tot":31.3,"pts":21.5,"reb":9.3,"ast":2.3,"tpm":0.3,"stl":1.3,"blk":2.0},
            "Jewell Loyd":       {"pos":"G","tc_tot":22.1,"pts":16.1,"reb":3.6,"ast":3.0,"tpm":1.5,"stl":1.2,"blk":0.2},
            "Jackie Young":      {"pos":"G","tc_tot":21.3,"pts":13.9,"reb":4.1,"ast":4.3,"tpm":1.1,"stl":1.0,"blk":0.3},
            "Chelsea Gray":      {"pos":"G","tc_tot":19.3,"pts":11.9,"reb":3.2,"ast":5.1,"tpm":0.9,"stl":1.2,"blk":0.3},
            "Chennedy Carter":   {"pos":"G","tc_tot":18.6,"pts":14.9,"reb":2.5,"ast":2.8,"tpm":0.3,"stl":1.0,"blk":0.3},
            "NaLyssa Smith":     {"pos":"F","tc_tot":17.8,"pts":11.3,"reb":7.1,"ast":1.1,"tpm":0.4,"stl":0.5,"blk":0.5},
        },
        "GS": {
            "Tiffany Hayes":     {"pos":"G","tc_tot":17.9,"pts":13.0,"reb":3.3,"ast":2.4,"tpm":1.0,"stl":1.0,"blk":0.2},
            "Janelle Salaun":    {"pos":"F","tc_tot":17.2,"pts":11.6,"reb":4.8,"ast":1.2,"tpm":1.5,"stl":0.7,"blk":0.1},
            "Gabby Williams":    {"pos":"F","tc_tot":15.4,"pts":8.5,"reb":4.0,"ast":2.9,"tpm":0.6,"stl":1.6,"blk":0.4},
            "Kayla Thornton":    {"pos":"F","tc_tot":13.1,"pts":7.7,"reb":4.3,"ast":1.2,"tpm":0.8,"stl":0.9,"blk":0.3},
            "Veronica Burton":   {"pos":"G","tc_tot":11.3,"pts":5.8,"reb":2.3,"ast":3.3,"tpm":0.6,"stl":0.8,"blk":0.3},
            "Kiah Stokes":       {"pos":"C","tc_tot":9.4,"pts":3.3,"reb":5.4,"ast":0.7,"tpm":0.1,"stl":0.5,"blk":1.1},
        }
    }
}
