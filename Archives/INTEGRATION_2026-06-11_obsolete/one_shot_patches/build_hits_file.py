"""TC HITS FILE GENERATOR - reads backtest CSVs, aggregates player hit stats."""
import os, glob, csv
from collections import defaultdict
from datetime import datetime, date
