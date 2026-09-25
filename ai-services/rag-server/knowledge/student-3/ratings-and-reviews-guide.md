# Ratings and Reviews Guide

Every attraction in the Local Experience & Attraction Recommender has a single overall rating on a 1-5 scale, stored alongside the attraction record, plus zero or more individual reviews, each with its own 1-5 rating and a free-text comment.

The overall rating is set when an attraction is created or edited and is not automatically recalculated from its individual reviews; a reviewer can leave a 3.5 comment on an attraction whose overall rating is 4.7, and both are shown independently. When comparing attractions, `attractions.search`'s `min_rating` filter applies to this overall rating field, not to any individual review's score.

Reviews in the seeded dataset skew positive: the lowest individual review score is 3.5 (on The Rocks Markets), and most reviews sit between 4.0 and 5.0. A review below 4.0 in this dataset is worth reading directly, since it is the exception rather than the norm and usually flags a specific, narrow complaint (for example, crowding or repeat stalls) rather than a fundamental problem with the attraction.

AI-Mode's recommendation and the RAG knowledge base both draw on the same underlying rating and review data, but answer different questions: AI-Mode ranks and recommends attractions for a stated preference, while a RAG question about ratings should be answered from this guide and the attraction-specific documents, not by re-deriving a recommendation.
