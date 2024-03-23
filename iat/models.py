"""
Implicit Association Test (IAT) experiment -- models.

Dynamic data points for IAT trials are collected in custom data model "Trial". See Konrad 2018 [1] for an article
on collection dynamic data with oTree.

[1] https://doi.org/10.1016/j.jbef.2018.10.006

November 2019
Markus Konrad <markus.konrad@wzb.eu>

Updated December 2020
Christoph Semken <dev@csemken.eu>
"""

import random

# required for custom data models:
from otree.db.models import Model, ForeignKey
from otree.export import sanitize_for_csv

from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)


author = 'Markus Konrad <markus.konrad@wzb.eu>'

doc = """
IAT – Implicit Association Test
"""

#
# configuration of stimuli: attribute and concept levels and stimuli words
# these are just made up stimuli; fill in your own
#

STIMULI = {
    'atributos': {
        'positivas': ['alegría', 'amor', 'paz', 'maravilloso', 'placer', 'glorioso'^,'risa', 'feliz'],
        'negativas': ['agonía', 'terrible', 'horrible', 'desagradable', 'malvado', 'malísimo', 'fallo', 'dolor']
    },
    'conceptos': {
        'español': ['español', 'murciano', 'canario', 'madrileño', 'andaluz', 'gallego'],
        'inmigrante': ['inmigrante', 'extranjero', 'árabe', 'africano', 'asiático', 'latino']
    }
}

STIMULI_LABELS = {
    ('atributos', 'positivas'): 'Palabras Positivas',
    ('atributos', 'negativas'): 'Palabras Negativas',
    ('conceptos', 'español'): 'Español',
    ('conceptos', 'inmigrante'): 'Inmigrante',
}

#
# configuration of practice and test blocks
#

BLOCKS = [
    {   # 1
        'label': 'Practice 1',
        'n': 10,      # this must match the number of stimuli per side
        'izquierda': [('conceptos', 'español')],
        'derecha': [('conceptos', 'inmigrante')],
        'is_practice': True
    },
    {   # 2
        'label': 'Practice 2',
        'n': 10,
        'izquierda': [('atributos', 'negativas')],
        'derecha': [('atributos', 'positivas')],
        'is_practice': True
    },
    {   # 3
        'label': 'Test 1',
        'n': 20,
        'izquierda': [
            ('atributos', 'negativas'),
            ('conceptos', 'español'),
        ],
        'derecha': [
            ('atributos', 'positivas'),
            ('conceptos', 'inmigrante'),
        ]
    },
    {   # 4: same as 3
        'label': 'Test 2',
        'n': 20,
        'izquierda': [
            ('atributos', 'negativas'),
            ('conceptos', 'español'),
        ],
        'derecha': [
            ('atributos', 'positivas'),
            ('conceptos', 'inmigrante'),
        ]
    },
    {   # 5
        'label': 'Practice 3 (reversed)',
        'n': 10,
        'izquierda': [('conceptos', 'inmigrante')],
        'derecha': [('conceptos', 'español')],
        'is_practice': True,
        'notice': 'CUIDADO, las categorías se han cambiado de sitio!',
    },
    {  # 6
        'label': 'Test 3',
        'n': 20,
        'izquierda': [
            ('atributos', 'negativas'),
            ('conceptos', 'inmigrante'),
        ],
        'derecha': [
            ('atributos', 'positivas'),
            ('conceptos', 'español'),
        ]
    },
    {  # 7: same as 6
        'label': 'Test 4',
        'n': 20,
        'izquierda': [
            ('atributos', 'negativas'),
            ('conceptos', 'inmigrante'),
        ],
        'derecha': [
            ('atributos', 'positivas'),
            ('conceptos', 'español'),
        ]
    },
]


class Constants(BaseConstants):
    name_in_url = 'iat'
    players_per_group = None
    num_rounds = len(BLOCKS)                  # number of blocks to play
    capture_keycodes = {'izquierda': ('KeyE', 'E'),
                        'derecha': ('KeyI', 'I')}
    next_trial_delay_ms = 250                 # delay between trials in millisec.


class Subsession(BaseSubsession):
    def creating_session(self):
        """
        Prepare trials for each round. Generates Trial objects.
        """

        # iterate through all players in all rounds
        trials = []
        for p in self.get_players():
            block_num = p.round_number - 1
            block_def = BLOCKS[block_num]    # get block definition for this round

            # create stimuli: class (attrib./concept) and level (e.g. pos./neg.) for left and right side
            stimuli = []
            for side in ('izquierda', 'derecha'):
                for stim_class, stim_lvl in block_def[side]:
                    stim_vals = STIMULI[stim_class][stim_lvl]   # concrete stimuli words
                    n_vals = len(stim_vals)
                    stimuli.extend(zip([side] * n_vals, [stim_class] * n_vals, [stim_lvl] * n_vals, stim_vals))

            # randomize order
            random.shuffle(stimuli)

            if len(stimuli) != block_def['n']:
                raise ValueError('the number of stimuli (%d) and the number of repetitions in the block definition '
                                 '(n=%d) do not match' % (len(stimuli), block_def['n']))

            # generate Trial object for each stimulus
            for trial_i, stim_def in enumerate(stimuli):
                side, stim_class, stim_lvl, stim = stim_def

                trials.append(Trial(
                    block=p.round_number,
                    trial=trial_i+1,
                    stimulus=stim,
                    stimulus_class=stim_class,
                    stimulus_level=stim_lvl,
                    player=p
                ))

        Trial.objects.bulk_create(trials)


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    pass


class Trial(Model):
    """
    Trial model holds all information for a single trial made by a player.
    This is a "custom data model" in a 1:n relationship between Player and Trial.
    It uses an otreeutils "CustomModelConf" for monitoring and exporting the collected data from this model.
    """
    block = models.IntegerField()  # block number (-> round number)
    trial = models.IntegerField()  # trial number in that round for that participant

    stimulus = models.StringField()          # shown word or name
    stimulus_class = models.StringField()    # words or names
    stimulus_level = models.StringField()    # pos/neg or tr/dt

    response_key = models.StringField()       # response: key that was pressed by participant
    response_correct = models.BooleanField()  # records whether response was correct
    response_time_ms = models.IntegerField()  # time it took until key was pressed since word/name was shown

    player = ForeignKey(Player, on_delete=models.CASCADE)  # make a 1:n relationship between Player and Trial

    class CustomModelConf:
        """
        Configuration for otreeutils admin extensions.
        """
        data_view = {  # define this attribute if you want to include this model in the live data view
            'exclude_fields': ['player'],
            'link_with': 'player'
        }
        export_data = {  # define this attribute if you want to include this model in the data export
            'exclude_fields': ['player_id'],
            'link_with': 'player'
        }


try:
    from otreeutils.admin_extensions import custom_export
except ImportError:
    def custom_export(players):
        """
        Export all IAT trials together with the standard fields `session` and `participant_code`
        """
        fields_to_export = ['block', 'trial', 'stimulus', 'stimulus_class', 'stimulus_level',
                            'response_key', 'response_correct', 'response_time_ms']
        yield ['session', 'participant_code'] + fields_to_export
        for trial in Trial.objects.all():
            yield [trial.player.session.code, trial.player.participant.code] \
                + [sanitize_for_csv(getattr(trial, f)) for f in fields_to_export]
