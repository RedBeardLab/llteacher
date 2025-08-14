# LLTeacher Project Overview

## What is LLTeacher?

LLTeacher is an innovative educational tool designed to help students learn with the assistance of AI (Large Language Models). The core concept is that teachers create homework assignments with reference solutions, and students interact with an LLM to solve these assignments step-by-step, receiving guidance rather than direct answers.

## Core Purpose

The project aims to create a learning environment where:
- **Teachers** can create structured homework assignments with detailed solutions
- **Students** can work through problems with AI assistance that guides them without giving away the answer
- **Learning** happens through guided discovery rather than passive consumption
- **Progress** is tracked and conversations are recorded for teacher review

## Key Innovation

Instead of students simply submitting final answers, the "submission" is the entire conversation with the AI tutor. This allows teachers to see:
- How students approached the problem
- What questions they asked
- Where they struggled
- How the AI guided them
- The learning journey, not just the destination

## Target Users

### Primary Users
- **Teachers**: Create assignments, review student progress, provide feedback
- **Students**: Work through assignments with AI assistance

### Secondary Users
- **Educational Administrators**: Monitor system usage and effectiveness
- **Researchers**: Study AI-assisted learning patterns

## Technical Architecture

LLTeacher is built as a Django web application with a monorepo structure using uv for package management. The system is designed to be:

- **Modular**: Separate apps for different concerns (accounts, homeworks, LLM interactions)
- **Extensible**: Easy to add new LLM providers or features
- **Scalable**: Can handle multiple teachers and students
- **Secure**: Role-based access control and proper authentication

## Core Workflow

1. **Teacher Setup**: Teacher creates homework assignment with detailed solution
2. **Student Access**: Student accesses assignment and starts working
3. **AI Interaction**: Student converses with LLM, which uses teacher's solution as guidance
4. **Progress Tracking**: System records all interactions and progress
5. **Teacher Review**: Teacher reviews student's learning journey and provides feedback
6. **Assessment**: Teacher grades based on process, not just final answer

## Success Metrics

The project aims to measure success through:
- Student engagement with assignments
- Quality of AI-guided learning conversations
- Teacher satisfaction with the review process
- Student learning outcomes and retention
- Time spent on assignments vs. traditional methods

## Current State

The project is functional but has identified fragility issues, particularly in the data model design. This documentation serves as a foundation for rebuilding a more robust version that addresses these architectural concerns.

## Next Steps

This documentation will be used to:
1. Identify the core strengths of the current system
2. Document the problematic areas that need redesign
3. Create a blueprint for a more robust architecture
4. Guide the development of the improved 2_llteacher version
