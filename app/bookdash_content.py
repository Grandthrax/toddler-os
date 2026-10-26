"""Book Dash editions. Template code GPLv3; licensed story content CC BY 4.0.

Original art/text credits and adaptation notices accompany every edition.
The wordless original deliberately has no invented narration.
"""

LICENSE = 'https://creativecommons.org/licenses/by/4.0/'
BASE = '/storybooks/bookdash/'
COME = {
    'publisher': 'Book Dash', 'license': 'CC BY 4.0', 'license_url': LICENSE,
    'source': 'https://bookdash.org/books/come-back-cat/',
    'creators': ['Nicola Rijsdijk — writer', 'Karen Lilje — illustrator', 'Sam Scarborough — designer'],
}
WHERE = {
    'publisher': 'Book Dash', 'license': 'CC BY 4.0', 'license_url': LICENSE,
    'source': 'https://bookdash.org/books/wheres-that-cat/',
    'creators': ['Sam Wilson — writer', 'Thea de Klerk — illustrator',
                 'Louis Greenberg — editor', 'Chenél Ferreira — designer'],
}


def choice(identifier, text, image, answer=''):
    return {'id': identifier, 'text': text, 'image': BASE + image + '.jpg', 'answer': answer}


def edition(identifier, title, cover, pages, stems, instructions, credits, mode, changes):
    return {'id': identifier, 'title': title, 'image': BASE + cover + '.jpg', 'pages': pages,
            'stems': stems, 'instructions': instructions, 'edition': mode,
            'description': 'Look and tell your story.' if mode == 'wordless' else
                           'Hear the original story.' if mode == 'original' else 'Type words. Make your version.',
            'credits': credits | {'changes': changes}}


# Publisher's English text, paired with its original twelve illustrations.
# Empty text denotes an original picture-only spread, not a missing recording.
COME_TEXT = [
    'Come back, cat! Play with me.',
    'Sit in your basket. Stay right here!',
    'Come back, cat! That’s way too high.',
    'Come back, cat! Don’t go outside.',
    '',
    'Come back, cat! That’s not yours.',
    'Come back, cat! What have you got?',
    'Come back, cat. That’s not your friend!',
    'Hello, cat! Are you back?',
    'Stay in your basket. It’s nap time now.',
    'Cat?',
    '',
]

BOOKS = [
    edition('come-back-cat-read', 'Come Back, Cat!', 'come-cover',
            [[choice('bd-come-cover', 'Come back, cat!', 'come-cover')]] +
            [[choice(f'bd-come-read-{n:02}', text, f'come-{n:02}')] for n, text in enumerate(COME_TEXT, 1)],
            ('',) * 13, (None,) * 13, COME, 'original',
            'Original English story and illustrations preserved. Presented as separate digital pages; '
            'local synthetic narration and word highlighting added. Original blank spreads remain wordless.'),
    edition('wheres-that-cat-look', 'Where’s That Cat?', 'where-cover',
            [[choice('bd-where-cover', '', 'where-cover')]] +
            [[choice(f'bd-where-look-{n}', '', f'where-page{n}')] for n in range(4, 16)],
            ('',) * 13, (None,) * 13, WHERE, 'wordless',
            'Original wordless story illustrations preserved in sequence. Digital page navigation added. '
            'There is no added story text or narration in this edition.'),
    edition('come-back-cat-make', 'Come Back, Cat! · My story', 'come-cover', [
        [choice('bd-come-start', 'come back, cat!', 'come-cover')],
        [choice('bd-come-sit', 'the cat can sit.', 'come-02', 'sit'),
         choice('bd-come-run', 'the cat can run.', 'come-05', 'run')],
        [choice('bd-come-sock', 'the cat has a sock.', 'come-06', 'sock'),
         choice('bd-come-snail', 'the cat has a snail.', 'come-07', 'snail')],
        [choice('bd-come-nap', 'the cat can nap.', 'come-12', 'nap'),
         choice('bd-come-play', 'the cat can play.', 'come-06', 'play')],
        [choice('bd-come-end', 'come back, cat!', 'come-12')],
    ], ('come back, cat!', 'the cat can …', 'the cat has a …', 'the cat can …', 'come back, cat!'),
            (None, 'bd-come-choose-1', 'bd-come-choose-2', 'bd-come-choose-3', None), COME, 'adaptation',
            'Shortened and rewritten as a five-page typed-choice story by Toddler OS. '
            'Original illustrations are reused in a new selection and order. New synthetic narration added.'),
    edition('wheres-that-cat-make', 'Where’s That Cat? · My story', 'where-cover', [
        [choice('bd-where-start', 'where is that cat?', 'where-cover')],
        [choice('bd-where-cat', 'i can see a cat.', 'where-page4', 'cat'),
         choice('bd-where-car', 'i can see a car.', 'where-page15', 'car')],
        [choice('bd-where-bug', 'i can see a bug.', 'where-page7', 'bug'),
         choice('bd-where-dad', 'i can see dad.', 'where-page4', 'dad')],
        [choice('bd-where-run', 'i can run.', 'where-page11', 'run'),
         choice('bd-where-sit', 'i can sit.', 'where-page7', 'sit')],
        [choice('bd-where-end', 'the cat is back.', 'where-page15')],
    ], ('where is that cat?', 'i can see a …', 'i can see …', 'i can …', 'the cat is back.'),
            (None, 'bd-where-choose-1', 'bd-where-choose-2', 'bd-where-choose-3', None), WHERE, 'adaptation',
            'New five-page typed-choice text by Toddler OS, inspired by the original wordless book. '
            'Original illustrations are reused in a new selection and order. New synthetic narration added.'),
]
TEMPLATES = {book['id']: book for book in BOOKS}
PROMPTS = {
    'bd-come-choose-1': 'What can the cat do? Type sit or run. Then press space or enter.',
    'bd-come-choose-2': 'What does the cat have? Type sock or snail. Then press space or enter.',
    'bd-come-choose-3': 'What can the cat do next? Type nap or play. Then press space or enter.',
    'bd-where-choose-1': 'What can you see? Type cat or car. Then press space or enter.',
    'bd-where-choose-2': 'What can you see now? Type bug or dad. Then press space or enter.',
    'bd-where-choose-3': 'What happens next? Type run or sit. Then press space or enter.',
    'read-finished': 'You finished your book. You can turn the pages or hear it again.',
    'picture-finished': 'You looked through your book. You can turn the pages and tell your own story.',
}
