#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vision")))

# Skip test gracefully if vision module is not yet implemented (TV2 task)
classifier_mod = pytest.importorskip("classifier", reason="Module vision/classifier.py not yet implemented by TV2")
angle_mod = pytest.importorskip("angle", reason="Module vision/angle.py not yet implemented by TV2")

PostureClassifier = classifier_mod.PostureClassifier
calculate_angle_vertical = angle_mod.calculate_angle_vertical

def test_angle_calculation_vertical():
    p_top = (100, 50)
    p_bottom = (100, 150)
    angle = calculate_angle_vertical(p_top, p_bottom)
    assert angle == 0.0

def test_angle_calculation_tilted():
    p_top = (100, 50)
    p_bottom = (150, 100) # dx = 50, dy = 50 -> 45 do
    angle = calculate_angle_vertical(p_top, p_bottom)
    assert round(angle, 1) == 45.0

def test_classifier_labels():
    clf = PostureClassifier(upright_max=15.0, slouching_min=25.0, leaning_min=20.0, window_size=3)
    
    # 10 do -> upright
    label, _ = clf.classify(10.0)
    assert label == "upright"
    
    # None -> unknown
    label, _ = clf.classify(None)
    # Sau 1 lan None, da so van la upright hoac dang cap nhat
    raw = clf.classify_raw(None)
    assert raw == "unknown"
