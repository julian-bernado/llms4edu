# slides for the ei fellows workshop
## brainstorm
the topic is "leveraging LLMs for data analysis in education research"

things that i know will appear in the course of this workshop are:
- llms for text (conversational?) annotation
    - present on it
    - have them do an interactive session where they try to pull out some interesting facets
- llms for OCR / structured information pulling
    - present on it
    - have htem do an interactive session where they're trying to turn unstructured data into a structured dataset
- issues with LLMs for research (privacy and replicability)
   - i think this gets split into its constituent issues and stuck after each of the sections? then turns into a discussion?

## slides
okay okay, i think it's shaping up something like this (topics are numbered, but then within each topic, we may have multiple slides. these will be delineated clearly if so and if not assume it all goes on one slide)
1. title slide
2. intro to me slide
3. signposting the different parts of the workshop
    - "i want to show you a couple concrete ways that LLMs can be used to do data analyses that would have previously been overly costly or time consuming"
    - list all of the coming topics
    - "my goal is that you'll come away with both ideas for how to use LLMs, and some intuition for why using LLMs requires special atttention in research"
4. llms for structured information pulling: explanation
    - "often data comes to us as a series of unstructured files"
    - "the data analysis procedures we work with typically want something closer to a table-like structure"
    - "so we're going to dive into turning this(1) into this (2)" (1) = some visual representation of a list of files, probably just a finder screenshot. (2) = tabular dataset mockup.
5. llms for structured information pulling: task description
    - SLIDE 1 BEGIN
    - MIT Open Courseware is a website where you can take view MIT classes and course materials online
    - These are undergraduate and graduate courses from various departments at MIT
    - I've scraped a random sample of 100 syllabi from MIT OCW
    - SLIDE 2 BEGIN
    - Your goal is to build and run a prompt that extracts some structured information from these syllabi and then report what you find
    - Some examples of structured information to extract:
        - Does the course have any prerequisites?
        - What percent of the course's grade comes from (exams/homework/reading/participation)?
        - How many required readings does the course have?
    - The goal here is to focus on extracting a well-defined (True/False) or number from each transcript
6. llms for structured information pulling: interactive portion
    - include the URL for people to go to the application
    - Maybe have the example research questions and/or some other things that will be helpful for them on the slide
    - I'm probably mostly just walking around the room at this time
7. llms for structured information pulling: discussion
    - Ask for open-ended reactions to their results
    - Ask some directed questions:
        - Were any of your results surprising?
        - (for the next slide) Did any people measuring the same thing get different results?
8. llm pitfall #1: reproducibility
    - Discuss three reasons: 
    - Different models (It's important to be transparent about model choice)
    - Benign prompt differences (Make sure you track which prompt your results came from)
    - Sampling (set temperature = 0)
9. llms for measurement: explanation
    - structured information extraction uses LLMs
    - measurement uses LLMs to interpret data
    - in reality, the boundary between these two tasks is not always so clear
    - we're going to use LLMs to help *understand* our data
10. llms for measurement: task description
    - SLIDE 1 BEGIN
    - These are transcripts from classroom conversations (it'll be the TalkMoves dataset)
    - This is a common test dataset in the education NLP space
    - These are K-12 Mathematics lessons
    - SLIDE 2 BEGIN
    - Imagine you want to understand some behavior in these classroom conversations
    - Some examples of questions to answer:
        - Praise after getting a problem correct
        - Student confusion/frustration
        - Classroom management
    - The goal here is to write up a description of some behavior in either teachers or students that might be present in the transcripts
11. llms for measurement: interactive portion
    - maintain the link to go to the application
    - Have helpful stuff on teh slide (prompting tips: give examples, try to give as much context as possible for what you're trying to do)
    - Walk throughout the room
12. llms for measurement: discussion
    - Ask what types of thigns people looked for
    - Directed questions:
        - Did anybody disagree with the examples that the LLM pulled out?
        - For those who did, how would you modify your prompt knowing how it extracted things?
        - (Segue into the next thing) If you were reading some research that was studying these transcripts and their outcome was anntoated by an LLM in this way. What problems do you foresee or disclaimer do you think is appropriate? What sources of bias can we imagine?
13. llm pitfall #2: validity
    - LLMs can quickly generate all these annotations
    - But how do we know the LLM was right? 
    - Human validation rounds, high agreement, unambiguous codebooks are all things to think about doing
14. llm pitfall #3: privacy, pricing
    - I want to leave you with what might be the most important one to keep in mind: Privacy and Pricing
    - When we use these LLMs, we're calling an API and sending our data to (OpenAI/Anthropic/Google)'s servers
    - For private data, which some of you may be working with, this can't be freely sent to a company's servers
    - Direct from an API, Sherlock, Locally are all routes from which you might be using LLMs
15. takeaways
    - 2 use cases
    - 3 pitfalls
    - Closing question: Maybe goes around to everyone, can you imagine using LLMs in your work this summer? Or the stuff you're interested in? What kinds of questions can it let you answer? All good if not
