"""
date: 2024-06-14
"""

from utils import components

class InscriptionWidget(components.Component):
    template_name = "agenda/components/inscription.html"

    def __init__(self, inscription):
        self.inscription = inscription

class InscriptionGroupWidget(components.Component):
    template_name = "agenda/components/inscription_group.html"

    def __init__(self, inscription_group):
        self.group = inscription_group