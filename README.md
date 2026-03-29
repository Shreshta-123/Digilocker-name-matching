# DigiLocker Name Matching Service

This project implements a name matching system similar to the one used in DigiLocker to verify user identities when fetching documents.

## Problem
Names across government documents may appear in different formats such as:
- Shreshta Eslampoor
- Eslampoor Shreshta
- Shreshta E.

These variations can cause document verification failures.

## Solution
This project uses multiple string similarity algorithms:

- Jaro-Winkler
- Metaphone
- SequenceMatcher

to detect similar names even if they are formatted differently.

## Features
- Preprocessing of names
- Phonetic matching
- Similarity scoring
- Result generation

## Folder Structure
data/ → input name datasets  
result/ → output results  
name_matching_shreshta.py → main algorithm

## Author
Eslampoor Shreshta
