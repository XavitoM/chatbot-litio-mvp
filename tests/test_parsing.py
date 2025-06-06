import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from main import extraer_nombre, extraer_rut, normalizar_rut


def test_extraer_nombre_introductory():
    assert extraer_nombre("hola, soy xavier martin 17088198-2") == "Xavier Martin"


def test_extraer_nombre_rut_prepend():
    assert extraer_nombre("17088198-2 xavier martin") == "Xavier Martin"


def test_extraer_nombre_middle_rut_word():
    assert extraer_nombre("xavier martin rut 17088198-2") == "Xavier Martin"


def test_extraer_nombre_rut_first():
    assert extraer_nombre("rut 17088198-2 xavier martin") == "Xavier Martin"


def test_extraer_rut_formats():
    assert extraer_rut("17088198-2") == "17088198-2"
    assert extraer_rut("17.088.198-2") == "17088198-2"
    assert extraer_rut("170881982") == "170881982"


def test_normalizar_rut():
    assert normalizar_rut("17088198-2") == "17088198-2"
    assert normalizar_rut("17.088.198-2") == "17088198-2"
    assert normalizar_rut("170881982") == "17088198-2"
    assert normalizar_rut("invalid") == ""

