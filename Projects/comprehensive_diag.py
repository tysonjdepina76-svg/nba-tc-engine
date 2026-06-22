#! /usr/bin/env python3
"""comprehensive_diag.py — full line-by-line assessment of every component"""
import json, os, sys, subprocess, time
from pathlib import Path
from datetime import datetime

def cmd(c):
    try:
        r = sub