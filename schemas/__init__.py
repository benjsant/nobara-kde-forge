#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Schemas Pydantic pour la validation des configs JSON."""

from .packages import Package, PackageList
from .flatpak import FlatpakApp, FlatpakList
from .external import ExternalPackage, ExternalPackageList
from .themes import Theme, ThemeList
from .profile import Profile, ProfileAptPackage, ProfileFlatpak, ProfileExternal, ProfileRemove
