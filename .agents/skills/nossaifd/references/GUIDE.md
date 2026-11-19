# Not so shitty AI first drafts

This guide is for documentation, READMEs and other prose that an AI model writes and a person reads. It
joins five sources:

- **ASD-STE100, Simplified Technical English.** Aerospace manuals use it, so that readers who are not
  native English speakers understand them. Most of its rules here come from memory, and
  [the list of them](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory) says which.
- **The plain-writing skill by Shreya Shankar.** It keeps prose plain and free of the habits of AI writing.
- **"Communicating Your Work", a tutorial by Rosalind Reid**, in two slide decks, the written reports and
  the tutorial deck. Rosalind Reid's decks give the order of a long document, several rules for sentences,
  and the rules for figures.
- **"Five Principles for Generating Readable AI Text in Bulk", a post by Shreya Shankar.** It gives the
  rules for short items that a person skims, such as titles and notifications.
- **The declaude skill by Oskar Austegard.** It finds the sentences that sound as if a model wrote
  them, and it gives the rules for the revision of a draft.

Each rule names its source and links to the place in it. A rule that comes from no source is this guide's
own, and it says so. The section "Sources" lists each place where this guide differs from a source.

Give this file to the model with the task, together with a glossary of the project's terms. Then run
`check.py` on the result, and read the result yourself. [The worked examples](EXAMPLES.md) show
many of the rules on real text from the sources.

## When to break a rule

Most rules of this guide are preferences. The few limits are the problems that `check.py` reports as
hard, for example a sentence of more than 40 words. A writer can break a preference when the story needs
it. For example, several questions in a row can build tension, and a report on a bug hunt can keep the
cause for the end. Think hard before you break a rule, and break it only for the story.

When Rosalind Reid and Shreya Shankar disagree about the same kind of text, this guide follows Rosalind
Reid. Both principles of this section are the project's own, the story before a rule and Rosalind Reid
before Shreya Shankar. [Why the rules](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md) gives each choice.

## Markdown comes first

The rules apply to the prose of a page, which is its paragraphs, list items, headings and image captions.
Markdown syntax always wins over a rule. The rules do not apply to these constructs:

- **Fenced code blocks and inline code.** Commands, code, file names and program output stay exactly as
  they are, with their own punctuation.
- **Tables.** A table cell can be a short phrase, a fragment or a value. Write the prose around the table
  by the rules.
- **Link targets, URLs and image paths.** The text of a link follows the rules, but its target does not.
- **Quoted examples.** Words in straight double quotes are words that the text talks about. They keep their
  own form, as in the list of words to avoid.
- **Front matter, HTML and comments.** Metadata at the top of a file, and HTML tags, keep their own syntax.

A rule about colons, dashes or quotes never applies to a character inside one of these constructs. The
section is this guide's own.

## Words

1. **Use simple, everyday words.** Choose the plain word when a longer word means the same thing:

   | Write | Not |
   |---|---|
   | use | utilize |
   | let | allow, enable |
   | make sure | ensure |
   | give | provide |
   | start | launch |
   | about | approximately |
   | through | via |
   | before | prior to |

   From: [Shankar's skill, rule 1](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L26),
   and the dictionary of STE, [from memory and not checked](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory).
2. **Use one term for one thing.** Keep a glossary of the project's terms, and use each term the same way
   every time. Do not change to a synonym for variety. A word keeps one meaning in the whole document.

   From: [STE, "one word, one meaning"](https://www.asd-ste100.org/about.html), and
   [Shankar's skill, rule 4](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L47).
3. **Define jargon the first time it appears on a page.** Use a technical term only when it is the most
   precise word, and say in plain words what it means. Do not invent jargon, and do not invent a
   hyphenated adjective that no dictionary has.

   From: Shankar's skill, [rule 2](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L32)
   and [rule 6](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L56).
4. **Write "e.g." or "for example" before an example.** Do not write "i.e." or "etc.". If a list is not
   complete, say so in words.

   From: [Shankar's skill, rule 11](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L105), which writes "e.g." before examples in a sentence. The
   words on "i.e." and "etc." are this guide's own.
5. **Do not add empty emphasis.** Remove a word that adds force but no fact. Examples are "really",
   "simply", "just", "actually", "crucial", "pivotal", "robust", "seamless", "powerful" and "matters". Also
   avoid the words that AI writing overuses, for example "delve", "leverage", "landscape", "tapestry",
   "unlock", "elevate" and "empower".

   From: Shankar's skill, [rule 1](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L26)
   and [rule 3](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L40).
6. **Do not use contractions in documentation.** Write "do not" and "it is". A reader who is not a native
   speaker reads the full form more easily. The rule is this guide's own. Shankar's skill lets a
   writer use contractions, so this guide changes it.

## Sentences

7. **Write complete sentences.** Each sentence has a subject and a verb. Do not write fragments, except in
   a table cell, a short list item or a label.

   From: [Shankar's skill, rule 8](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L74).
8. **Keep a sentence to about 20 to 25 words, and to one or two clauses.** An occasional longer sentence is
   fine when its punctuation makes it clear. If a sentence needs three clauses, make two sentences, or use
   a list. But do not cut one thought into a stack of short sentences. Join two related clauses with
   "and", "but", "because" or "so". `check.py` notes a sentence of more than 25 words. It fails one of more
   than 40, which is this guide's own limit.

   From: the writing rules of STE, [from memory and not checked](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory) for the 25 words, and Shankar's
   skill, [rule 11](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L105)
   and [rule 12](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L118).
9. **Use mostly the active voice, mix in the passive where it helps, and put each action in a verb.** Rosalind
   Reid says that a mix of active and passive sentences can help. Prefer simple verb forms. Write "the server
   reads the file" and not "the file is read by the server". Write "runs" and not "is running". Write "we
   measured the latency" and not "a measurement of the latency was made". A passive, an -ing form or a
   noun for an action is not wrong when it does a job:
   - A passive is correct when it puts the known information first, as rule 13 asks. It is also correct
     when the actor is unknown.
   - A noun for an action is correct when it names the action of the sentence before, as in "The
     measurement showed a delay".
   - An -ing form is allowed, but prefer the simple form. An -ing clause at the end of a sentence must
     add a fact, as in "The script reads each file, skipping the empty ones". Do not end a sentence with
     one that only claims importance, as in "The team released version 2, marking a turning point".

   From: the writing rules of STE, [from memory and not checked](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory), and Rosalind Reid, written
   reports, [pages 13 and 14](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf)
   for actions in verbs and [page 15](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf)
   for the voice. The passive for an unknown actor is this guide's own. STE, from memory and not checked, asks for the active voice, and
   this guide follows Rosalind Reid. The rule for an -ing clause at the end follows
   [Oskar Austegard's declaude skill, register entry 25](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L419),
   which removes a clause at the end that only claims importance.
10. **Put not more than two nouns in a row.** Break a longer group with "of", "for" or "in". Write "the
    size of the terminal font" and not "the terminal font size setting". Write "the format of the cache
    key" and not "the cache key format". A standard term of the field, such as "foreign key constraint",
    keeps its nouns. So does a group of nouns that the document defines once and then uses as a name.

    From: the writing rules of STE, [from memory and not checked](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory), which allow three nouns. The
    limit of two and the term of the field come from [Oskar Austegard's declaude skill, register entry 53](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L1185), and this guide follows
    it.
11. **Say exactly what happens.** Name who or what does the action, and by what means. Remove side clauses
    that add no fact, for example "as we move forward" or "for the time being".

    From: [Shankar's skill, rule 13](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L136).
12. **Put the verb close to its subject.** A reader holds the subject in mind until the verb comes. Do not
    put a long phrase between them. Write "The backup script stops when the disk is full or the network
    drops." Do not write "The backup script, when the disk is full or the network drops, stops."

    From: [Rosalind Reid, written reports, page 12](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf).
13. **Put the known information first and the new information last.** Start a sentence with what the
    reader already knows, for example the subject or a link to the sentence before. End it with the new
    fact. Rosalind Reid calls the end of a sentence the "stress position". The reason that a reader gives
    the end the most weight is this guide's own. The new fact at the end then leads into the next
    sentence. Write "The build failed on Monday. The cause of the failure was an expired certificate." Do
    not write "An expired certificate was the cause of the failure of the build on Monday."

    The rule is for prose that a person reads in order. Two other kinds of text differ. A speaker often
    gives the news first and the context after it, as Rosalind Reid shows. A short item in a list starts
    with the words that make it different, by rule 46.

    From: Rosalind Reid, written reports, [pages 6 and 7](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf)
    and [pages 9 to 11](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf).

## Instructions

14. **Write an instruction as a command.** Write "Open the file" and not "You should open the file" or "The
    file can be opened".

    From: the writing rules of STE, [from memory and not checked](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory).
15. **Give one instruction in one sentence, in the order the reader does it.** Use a numbered list, or
    "First", "Second" and "Third", for a sequence. Two actions that happen at the same time can share a
    sentence.

    From: the writing rules of STE, [from memory and not checked](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory), and
    [Shankar's skill, rule 9](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L83).
16. **Put a condition first.** Write "If the test fails, read the log" and not "Read the log if the test
    fails". Keep an instruction to about 20 words, as rule 8 says.

    From: the writing rules of STE, [from memory and not checked](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory).
17. **Start a warning with a short command, then give the reason.** Write "Do not put the address on a
    slide. Anyone with the address can run commands as you."

    From: the writing rules of STE, [from memory and not checked](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory).

## Paragraphs

18. **Start each paragraph with a topic sentence.** Then give support, with a fact or an example. Start
    more support with a plain word, for example "For example", "Also" or "But".

    From: [Shankar's skill, rule 10](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L94).
19. **Keep a paragraph to six sentences or fewer.** Do not give three or more examples in a row for the
    same point.

    From: the writing rules of STE, [from memory and not checked](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md#asd-ste100-rules-from-memory) for the six sentences, and
    [Shankar's skill, rule 11](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L105)
    for the examples.

## Long documents

These rules are for a document that a reader takes in whole and in order, for example a report, a
proposal or a design document. A report can be a blog post, and its style can be conversational. The
rules come from the tutorial by Rosalind Reid. Her written reports say that a report tells the same story
as a talk, with more detail. So this guide takes the parts of the story from
her tutorial deck. A rule that adds advice of this guide's own says so.

Some documents have another order:

- **A README** starts with what the project does. Then it says how to start. The motivation comes after
  that, if at all.
- **A status note, a pull request and a summary** start with the result, and then give the background.
  [Shankar's skill](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L270)
  gives the order for a busy reader.
- **A reference page**, such as a list of options, follows the order in which a reader looks things up.

The order of a README is this guide's own. It is not Rosalind Reid's.

20. **Tell the story of a problem and how it was solved.** Give the document these parts, in this order:
    - **Summary.** A few sentences at the start of every report. Usually they state the result. A report
      can be a story with a climax, such as a bug hunt with wrong paths. Then the summary states the
      problem and gives the reader the puzzle. It does not give away the climax. Write "The build slowed
      from 4 minutes to 40 over one week, and the log of that week shows no commit to the build files. We tried three
      fixes, and each one failed." Do not write a teaser that says content follows but names none of it, as in
      "Read on to see how we found the cause". The summary is this guide's own rule, and not Rosalind
      Reid's. The ban on the teaser comes from Oskar Austegard's declaude skill,
      [register entries 8](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L175) and [42](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L843).
    - **Motivation.** Why the reader should care about the work.
    - **Description.** The problem in detail, and how the work broke it into parts.
    - **Approach.** What was done, and why.
    - **Learning.** What the work showed, and what did not work.
    - **Result.** The conclusion, what it means and what follows from it.

    The parts can be sections, or paragraphs in a short document. The start and the end are general, and the
    middle is specific. Rosalind Reid draws this shape as an hourglass
    ([Rosalind Reid, tutorial deck, page 16](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf),
    and [Rosalind Reid, written reports, page 4](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf)).

    From: Rosalind Reid, tutorial deck, [pages 15 and 16](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf),
    and written reports, [pages 2 to 4](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf).
21. **Start with the motivation for this reader.** Say what larger problem the work is part of, what the
    reader gains from it, and what it gives other people. Start with why the work was necessary.

    From: [Rosalind Reid, tutorial deck, pages 17 and 18](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf).
    This guide adds a warning of its own. Do not start with the history of the project or with the method.
    An AI model often starts a draft with what it built.
22. **Choose the motivation, the technical level and the content for the reader.** Name the reader before
    you write, for example a manager who decides or an engineer who maintains the code. Every reader that
    the document is for must be able to follow it.

    From: Rosalind Reid, tutorial deck, [page 19](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf),
    and written reports, [page 22](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf).
    This guide adds that two different readers can need two different documents.
23. **Describe the problem before the approach.** Give the technical background and the practical reason
    that the problem is important. Then give the earlier work and the solution that the work tests. A
    reader who does not know the problem cannot judge the solution.

    From: [Rosalind Reid, tutorial deck, pages 21 and 22](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf).
24. **Give the approach the most care, and keep only what supports its main points.** The approach is the
    most important part of the story. Write an outline of the main points before you write the text. Then
    remove each detail that does not support one of them.

    From: [Rosalind Reid, tutorial deck, pages 24 and 25](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf).
    This guide adds that the approach usually needs the most space.
25. **Report what did not work.** Say what the work showed, what failed and what the failure taught. A
    report that gives only the successes leaves out what the next person needs to know.

    From: [Rosalind Reid, tutorial deck, page 36](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf).
26. **End with the result and what it means.** State the conclusion, what it means and what follows from
    it.

    From: [Rosalind Reid, tutorial deck, page 38](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf).
    This guide adds that the result also states its limits.
27. **Credit the people and the sources.** Name the people who helped with the work, and the earlier work
    that the document uses.

    From: [Rosalind Reid, tutorial deck, page 39](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf).
28. **Revise the draft for flow.** Read the draft as the reader reads it. Join related sentences with a
    plain word, for example "Also" or "In addition". Remove a phrase that repeats, and each word that adds
    no fact.

    From: Rosalind Reid, written reports, [page 11](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf)
    and [pages 16 and 17](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf).

## Figures and equations

The rules in this section also come from Rosalind Reid.

29. **Use words, pictures and equations each for its own work.** Words explain, and connect the parts of
    the argument. A picture shows a pattern, a structure or a method. An equation gives the exact form of a
    relation to a technical reader.

    From: [Rosalind Reid, written reports, pages 19 to 21](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf).
30. **Explain every figure in the text.** Say what the figure shows, and what the reader must see in it.
    Label its parts in plain words. Make a data figure lead the reader to the important result, and remove
    what does not help. Do not draw every link of a large network when a simple plot shows the result.
    Do not draw bars in three dimensions.

    From: Rosalind Reid, written reports, [page 19](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf),
    and tutorial deck, [page 30](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf),
    [pages 51 to 54](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf)
    and [page 59](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf).
31. **Explain every equation in words.** Say what each symbol means and what the equation says. A reader
    who skips the equation must still follow the argument.

    From: Rosalind Reid, tutorial deck, [page 30](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf),
    and written reports, [page 21](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf).
    The last sentence of the rule is this guide's own.

## Tone

32. **Write literal headings.** Do not write a catchy heading, a slogan or a clever label. A heading says
    what the section is about, for example "Move a file that has unsaved edits" and not "The point of no
    return". When a section makes one point, name the concrete thing, as in "When create_session fails".
    Do not name a topic area with an -ing form or an abstract noun, as in "Spawn availability" or
    "Detecting a parked child". In a reference, such as this guide, a label for a group of entries is
    correct, as in "Punctuation and formatting". The title of a task in progress in a list keeps its -ing
    form, by rule 45. The text under the heading can be conversational.

    From: [Shankar's skill, rule 7](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L63).
    The rule against a topic area comes from [Oskar Austegard's declaude skill, register entry 41](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L816).
33. **Use an analogy, a metaphor or humor when it explains the work.** Rosalind Reid recommends them for
    written, visual and spoken work
    ([Rosalind Reid, tutorial deck, page 40](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf)).
    State the literal fact in the next sentence, for a reader who is not a native speaker. Remove a
    metaphor that adds no fact, because an AI model often writes one.

    From: Rosalind Reid. The literal fact after the analogy is this guide's own.
    [Shankar's skill, rule 21](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L222) forbids analogy and metaphor, and this guide follows Rosalind Reid.
34. **Do not give objects fake agency.** A tool can return, write or read. But do not write as if a system
    decides or intends something, when a person or a process is the real actor. Do not give a thing a verb
    that needs a mind, as in "The median hides it" or "The docstring promises". A pairing that readers
    know is correct, as in "The table shows" or "The measurement showed a delay".

    From: [Shankar's skill, rule 20](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L214).
    The verbs that need a mind, and the pairings that readers know, come from [Oskar Austegard's declaude skill, register entry 4](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L73).
35. **State what a thing is.** Do not write "not just X, but Y" or "not only X, it is Y".

    From: [Shankar's skill, rule 22](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L230).
36. **Ask a rhetorical question only when the reader has it, and answer it in full sentences.** Do not ask
    a question that you answer at once with a fragment, as in "So how does it fail? Mostly by not
    finishing." Write "Why does a retry make the bug worse? Each retry takes a new lock, so two retries can
    wait on each other." Prefer one question at a time. Several in a row are correct only in a story,
    where they are the questions that the people in it asked.

    From: [Shankar's skill, rule 23](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L240),
    which forbids two or more in a row. This guide lets a writer ask them for the story. The ban on the
    fragment answer comes from [Oskar Austegard's declaude skill, register entry 10](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L201).
37. **Do not start a sentence with a vague "This", "That", "These" or "Those".** Name the thing. Write "The
    flag lets a move discard edits" and not "This lets a move discard edits". Write "it" when only one thing
    could be meant. Write the noun when the sentence before names two things, such as a parent and a child.

    From: [Shankar's skill, rule 24](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L248).
    The choice of "it" comes from [Oskar Austegard's declaude skill, register entry 40](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L788).
38. **Do not open with a count.** Do not write "Three things to know." State the first thing. If there are
    many things, use a list. A count is correct in front of the list that it counts when it also says what
    the items share or how they differ, as in "Three shapes, and the fix differs for each:". "Two
    cautions:" says only the count, so delete it and start with the first caution.

    From: [Shankar's skill, rule 25](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L255).
    The count in front of a list comes from [Oskar Austegard's declaude skill, register entry 38](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L720).

## Punctuation and formatting

39. **Do not use dashes or middle dots.** Do not use an em dash or an en dash, and do not use the middle
    dot as a separator. Write a range with "to", as in "10 to 20 seconds".

    From: [Shankar's skill, rule 15](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L163).
40. **Do not join two clauses with a colon in prose.** Write two sentences. A colon is correct before a list,
    and after a short label such as "Summary:" or "Note:". A semicolon is correct between the steps of a
    sequence, and nowhere else in prose.

    From: Shankar's skill, [rule 8](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L74)
    and [rule 16](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L170).
    The semicolon between steps comes from Shankar's rule 9.
41. **Use straight quotes**, " and ', not curly quotes.

    From: [Shankar's skill, rule 17](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L181).
42. **Use sentence case in headings.** Write "How to install the tool" and not "How To Install The Tool".

    From: [Shankar's skill, rule 18](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L185).
43. **Use bold to set one thing off from the next.** Bold the first words of a list item or a paragraph
    when they are a name that the reader looks for, such as an option, a term or a case. Write
    "**--dry-run** prints the changes and writes nothing." Do not bold a label that repeats the sentence,
    as in "**Performance:** Performance has been improved". Bold the names of things the reader must find
    on a screen, for example a button. Do not use bold for emphasis in the middle of a sentence.

    From: [Shankar's skill, rule 18](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L185),
    which forbids bold for decoration. The two uses of bold are this guide's own. The test of a name that
    the reader looks for comes from [Oskar Austegard's declaude skill, register entry 29](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L518).
44. **Use lists and tables where they help, and not more.** In prose, keep a list to about four items, and
    nest the items if there are more. On a reference page, a table is the clearest form for options,
    commands and keys.

    From: [Shankar's skill, rule 19](https://github.com/docwriter-org/plain-writing-skill/blob/f0d3630983ac7a82aa580f1c1509d72df739ee12/skills/plain-writing/SKILL.md?plain=1#L190).
    The advice on a reference page is this guide's own.

## Short items read in bulk

These rules are for many short items that a person skims, for example titles, headings, list items,
notifications, table cells and rows in a dashboard. A reader of such a list often reads only the first two
words of each item. The other rules of this guide still hold, except where a rule below replaces one of
them. The rules come from the post by Shreya Shankar, and this guide states them in its own words.

45. **Start each item with its subject or its verb.** A reader takes the first noun as the actor and the
    next verb as the action. Write "The agent fixed the login bug" and not "Login bug fixed by the agent".
    If every item has the same subject, leave it out and start with the verb. Put the verb in the tense
    that the reader expects. For the title of work in progress, the -ing form is correct, as in "Measuring
    the latency". Elsewhere, rule 9 prefers the simple form.

    From: [Shankar's post, principle 1](https://fsdatalab.github.io/blog/agent-text-at-scale/#1-match-how-human-readers-parse-sentences).
46. **Put first the words that make an item different.** Find the words that tell the item apart from the
    other items, and move them to the start. Write "Shipped: the order 1001" and not "Your order 1001 has
    shipped". In an item, the rule takes the place of rule 13.

    From: [Shankar's post, principle 2](https://fsdatalab.github.io/blog/agent-text-at-scale/#2-put-the-most-important-words-first).
47. **Give every item the same structure and the same words.** Use one pattern in all the items, for
    example a subject, a verb in the present tense and an object. Use one word for each thing in all the
    items, as rule 2 says.

    From: [Shankar's post, principle 3](https://fsdatalab.github.io/blog/agent-text-at-scale/#3-use-the-same-structure-and-the-same-vocabulary).
48. **Make an item different only when the difference means something.** A reader thinks that a difference
    in length, structure or words carries a meaning. If one item names a version number, the reader asks
    why the other items do not. Give each item the same parts. Put the extra detail where the reader can
    open it.

    From: [Shankar's post, principle 4](https://fsdatalab.github.io/blog/agent-text-at-scale/#4-use-variation-only-to-show-a-meaningful-difference).
49. **Choose verbs whose feeling shows the purpose of the text.** In a list of complaints, write "Users
    complain that the app freezes". In a list of praise, write "Users love the new course". The rule also
    holds in prose. Rule 5 still removes a word that adds force but no fact.

    From: [Shankar's post, principle 5](https://fsdatalab.github.io/blog/agent-text-at-scale/#5-align-the-connotation-of-verbs-with-the-purpose-of-the-dashboard).

## Patterns of model prose

These rules are for the revision of a draft. An AI model writes some sentences to sound like a finding,
and not to give one. The rules come from the declaude skill by Oskar Austegard.

The skill by Oskar Austegard lists 56 patterns in a file that it calls the register. For most patterns
the register gives a pair of sentences from real text, before and after the revision. This guide states
the rules in its own words. The register, with all its examples, is in
`.agents/skills/declaude/references/register.md`. Read it after you write the draft, and not before,
as the skill asks.

50. **State a finding, and do not stage it.** A staged sentence makes the reader feel that a finding
    arrives. A stated sentence gives the finding. Ask of each sentence whether it states the finding or
    stages it. For example, do not say what a thing is not before you say what it is, unless the reader
    believed the wrong thing. Do not tell the reader which sentence is important.
    Do not end a paragraph with a short, quotable line that repeats the paragraph. Write "It is a
    non-answer rather than a wrong answer" and not "It is not a wrong answer. It is a non-answer." Rule 35
    is one case of this rule.

    From: [Oskar Austegard's declaude skill, register entries 1 to 23](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L10), and
    [entries 37 to 42](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L687).
51. **Remove the defaults of chatbot prose.** Write "is" and not "serves as". Do not add a clause with an
    -ing form at the end of a sentence to claim that the fact is important. Give the number of items that
    the content has, and not three because three sounds complete. Write a range only when it has a scale,
    as in "from 2 to 8 bits". Remove the words of a chat reply, for example "I hope this helps".

    From: [Oskar Austegard's declaude skill, register entries 24 to 36](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L385). The register
    takes them from the Wikipedia page "Signs of AI writing", through the humanizer skill.
52. **Give the evidence for each claim of certainty.** An adverb such as "plainly" or "quietly", a
    compound such as "byte-identical", and a word such as "nothing" or "never" each claim a check. Say what
    was run, what came back and what scope was checked. Write "The fit has one parameter per cluster and
    none per week" and not "Nothing in the fit varies with time".

    From: [Oskar Austegard's declaude skill, register entries 43 to 47](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L865). The
    skill takes them from Louis Abraham's study of the words in pull requests, "load-bearing".
53. **Do not tell the reader that you are honest, and do not grade your own text.** Remove "to be honest",
    "to be clear" and "I will not pretend". Do not write "that is why the transcript was important" about
    an earlier paragraph, or "that is the whole point" about one part of a thing.

    From: [Oskar Austegard's declaude skill, register entries 48 to 52](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L1028). The
    skill takes them from Simon Willison's "llm-cliche-highlighter".
54. **Do not pack a claim into fewer words than a reader can parse.** Keep "that" in a long clause, give
    the verb soon after its subject, and use a plain verb and not a noun as a verb. Rules 10 and 12 are
    cases of this rule. A revision that is shorter and harder to read is worse than the draft.

    From: [Oskar Austegard's declaude skill, register entries 53 to 56](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/references/register.md?plain=1#L1146). The register
    takes them from a paper by Clark, Martin and Mahowald, arXiv 2610.29162.
55. **Keep every claim of the draft in the revision, and add none.** Keep each number, name, ranking and
    hedge that has content. Do not add a fact, a name, a number, a date or a citation that the draft or
    the author did not give. If the draft disagrees with itself, tell the author, and do not choose a
    version. Keep word for word each bad example that the page shows on purpose, even when a tool marks
    it. A bad example teaches only next to its fix.

    From: Oskar Austegard's declaude skill, ["Do not invent specifics"](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/SKILL.md?plain=1#L29) and
    [steps 5 and 6 of its workflow](https://github.com/oaustegard/claude-skills/blob/6baa7290da972191749acda03c63297e67b3fc26/declauding/SKILL.md?plain=1#L275).

## Check the result

`check.py` measures the rules that a program can measure:

```
uv run --no-project python check.py page.md [page.md ...]   # hard problems fail the check
uv run --no-project python check.py -v page.md              # also show the soft notes, for a person to judge
```

The hard checks find these problems:

- a sentence of more than 40 words, or a paragraph of more than six sentences
- a contraction, a dash, a middle dot or a curly quote
- a colon between two clauses
- "i.e.", "etc.", or a "not just" construction
- a count at the start of a paragraph, or a vague "This is"

The soft notes are for a person to judge. They show a sentence of more than 25 words, or an instruction of
more than 20. They also show two questions in a row, -ing forms, possible passives and semicolons. The last
notes are nouns that name an action, sentences that may have three clauses, and words with a simpler
alternative.

The program cannot judge meaning, tone or a missing definition.

Next, give the draft to an agent that did not write it, such as a subagent. That agent revises the
draft with the declaude skill by Oskar Austegard, in `.agents/skills/declaude/`. Its file `SKILL.md`
gives the steps. Its linter marks the patterns of rules 50 to 54 that a program can find,
and its diff shows each claim that a revision lost or added:

```
uv run --no-project python .agents/skills/declaude/scripts/declaude_lint.py --skip-quoted page.md
uv run --no-project python .agents/skills/declaude/scripts/declaude_diff.py draft.md page.md
```

Its author says that the linter finds about two thirds of what a careful reading finds, so the agent
also reads each sentence. Then run `check.py` again, and fix only what the revision broke. Run the linter
once more, to check that the fixes brought back no pattern. Then read every page yourself. In every
step, keep each bad example that the page shows on purpose, as rule 55 says.

## Sources

- **ASD-STE100, Simplified Technical English (STE)**, Issue 8, at https://www.asd-ste100.org/about.html.
  The AeroSpace and Defence Industries Association of Europe (ASD) owns it, and aircraft makers write their
  maintenance manuals in it for readers who are not native English speakers. Andrej Karpathy suggested on X
  that the same rules suit text that AI models write. The rules for words, sentences, instructions and
  paragraphs come from it. Only its about page was read. That page confirms the purpose of STE and its
  rule of one word for one meaning. Every other rule that this guide gives to STE comes from memory. So do
  the few word swaps of rule 1 from its dictionary. So each of their credits says "from memory and not
  checked".
- **The plain-writing skill by Shreya Shankar**,
  https://github.com/docwriter-org/plain-writing-skill, at commit f0d3630, under the MIT licence, copyright
  (c) 2026 Shreya Shankar. The rules for tone, punctuation and the patterns of AI writing come from it,
  and several rules for words and sentences. This guide states the rules in its own words. It changes four
  of them:
  - Rule 6 forbids contractions in documentation. Shankar's rule 5 lets a writer use them.
  - Rule 8 keeps a sentence to about 20 to 25 words. Shankar's rule 12 prefers long sentences. Both rules
    forbid a stack of short sentences.
  - Rule 36 lets a writer ask several rhetorical questions in a row for the story. Shankar's rule 23 forbids them.
  - Rule 33 follows Rosalind Reid. Shankar's rule 21 forbids analogy and metaphor, and her rule 7 keeps
    the writing boring. Rule 32 keeps only the headings literal.
- **"Five Principles for Generating Readable AI Text in Bulk", a post by Shreya Shankar**, 29 October
  2026, at https://fsdatalab.github.io/blog/agent-text-at-scale/. Rules 45 to 49 come from its five
  principles. The post shows them on lists of titles, emails, summaries and dashboards. Rule 49 also lets
  a writer use the verbs with a strong feeling in prose.
- **"Communicating Your Work", a tutorial by Rosalind Reid**, which she taught in the course AC297r at the
  Institute for Applied Computational Science at Harvard in March 2015. Rosalind Reid was the editor of
  American Scientist magazine from 1992 to 2008. She gave permission to use her material, on the
  condition that this guide credits her wherever it uses her work. This guide gives her advice in its own
  words, and it names her in each rule that uses it. Text that comes from her work must keep its credit to
  Rosalind Reid, in every copy and in every changed version of this guide. The MIT licence of this
  repository does not remove that condition. Her PDFs are her own work, and they are not under the MIT
  licence. The tutorial has two decks:
  - [Written reports](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-written-reports.pdf),
    23 pages. It gives the rules for sentences on pages 5 to 17, and the work of words, pictures and
    symbols on pages 19 to 21. On page 18 she thanks the Duke Scientific Writing Resource.
  - [Tutorial deck](https://github.com/rahuldave/nossaifd/blob/main/sources/reid/reid-2015-communicating-your-work-deck.pdf),
    59 pages, 25 March 2015. It gives the parts of the story on pages 15 to 39, and advice on figures on
    pages 30, 31 and 51 to 54.

  Rules 9, 12, 13, 20 to 31 and 33 use her work. Where she and Shankar disagree, this guide follows
  Rosalind Reid:
  - **Analogy, metaphor and humor.** Rosalind Reid recommends analogy, an informal style, metaphor and
    humor for written, visual and spoken work. She gives them on pages 40 to 57 of the tutorial deck, and
    on pages 19 and 20 of the written reports. Rule 33 lets a writer use them, with the literal fact in the next
    sentence.
  - **The voice.** She prefers the active voice, and she says that a mix of active and passive sentences
    can help. Rule 9 follows her.

  This guide differs from Rosalind Reid in one place. Her story ends with the result. This guide starts
  every report with a summary, and a README with what the project does.
- **The declaude skill by Oskar Austegard**, which he calls declauding, in
  https://github.com/oaustegard/claude-skills, folder `declauding`, version 0.14.0 at commit 6baa729, under the MIT licence, copyright (c) 2025 Oskar
  Austegard. Rules 50 to 55 come from it, and rules 9, 10, 20, 32, 34, 36, 37, 38 and 43 take parts of
  it. This repository ships the skill in `.agents/skills/declaude/`, with its licence and three changes.
  Its register gives a pair of sentences, before and after, for most patterns. The README of the skill
  names its sources, which are the Wikipedia page "Signs of AI writing", the humanizer skill, Louis
  Abraham, Simon Willison, and Clark, Martin and Mahowald. Where the skill and an earlier version of a rule
  above disagreed, the project's author chose. [Why the rules](https://github.com/rahuldave/nossaifd/blob/main/docs/why.md)
  lists each choice. A sample of an author's writing wins over the register, but not over the hard limits of this
  guide.
