# OPAD (One Paragraph A Day)

OPAD is an AI-powered system that automatically creates educational reading materials from news articles for language learners. Using [crewAI](https://crewai.com), it finds relevant news articles, selects the most appropriate one, and adapts it to match the learner's proficiency level.

## Project Overview

OPAD transforms current news articles into personalized reading materials by:
1. **Finding** recent news articles on a specified topic
2. **Selecting** the best article based on topic relevance, difficulty, and educational value
3. **Adapting** the selected article to match the target language level and length

## Purpose

The goal of OPAD is to provide language learners with:
- **Current, relevant content**: Real news articles instead of outdated textbook materials
- **Appropriate difficulty**: Content adapted to the learner's proficiency level
- **Complete source attribution**: Original source information preserved for reference
- **Personalized learning**: Materials tailored to specific topics, languages, and levels

This enables learners to practice reading with engaging, up-to-date content while maintaining appropriate difficulty levels for effective language acquisition.

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:

```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```
### Customizing

**Add your `OPENAI_API_KEY` into the `.env` file**

- Modify `src/opad/config/agents.yaml` to define your agents
- Modify `src/opad/config/tasks.yaml` to define your tasks
- Modify `src/opad/crew.py` to add your own logic, tools and specific args
- Modify `src/opad/main.py` to add custom inputs for your agents and tasks

## Running the Project

To kickstart your crew of AI agents and begin task execution, run this from the root folder of your project:

```bash
$ crewai run
```

This command initializes the opad Crew, assembling the agents and assigning them tasks as defined in your configuration.

This example, unmodified, will run the create a `report.md` file with the output of a research on LLMs in the root folder.

## Understanding Your Crew

The opad Crew is composed of multiple AI agents, each with unique roles, goals, and tools. These agents collaborate on a series of tasks, defined in `config/tasks.yaml`, leveraging their collective skills to achieve complex objectives. The `config/agents.yaml` file outlines the capabilities and configurations of each agent in your crew.

## Changelog

### Version 0.1.0
- Improved JSON output format validation
- Added source URL and author verification
- Enhanced level-based vocabulary filtering
- Improved markdown section structure
- Added Next.js web viewer for reading materials
- Implemented interactive vocabulary click feature

## Support

For support, questions, or feedback regarding the Opad Crew or crewAI.
- Visit our [documentation](https://docs.crewai.com)
- Reach out to us through our [GitHub repository](https://github.com/joaomdmoura/crewai)
- [Join our Discord](https://discord.com/invite/X4JWnZnxPb)
- [Chat with our docs](https://chatg.pt/DWjSBZn)

Let's create wonders together with the power and simplicity of crewAI.
