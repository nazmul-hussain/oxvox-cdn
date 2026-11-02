# oxvox-cdn data schema

Static, versioned content served from GitHub (jsDelivr CDN). The Flutter app reads these files.
User data never lives here; it lives on the device now and in MongoDB Atlas later.

## Content (this repo, read-only for the app)
- `v1/manifest.json`: schemaVersion, contentVersion, file paths.
- `v1/data/words.json`: array of word documents (`_id` = `id`).
- `v1/data/listening_lessons.json`: array of lesson documents.

## MongoDB Atlas target (for future sync and features)
Collections map 1:1 to the documents below. Import the CDN JSON with `mongoimport --jsonArray`.

| Collection | Purpose | Key fields |
|---|---|---|
| `words` | Oxford word bank | `_id`, `word`, `cefr`, `lists[]`, `meaning`, `example`, `examples[]`, `synonyms[]`, `antonyms[]` |
| `lessons` | Listening lessons | `_id`, `num`, `title`, `audio`, `lines[]`, `voice`, `duration` |
| `users` | Profile and settings | `_id` (auth uid), `displayName`, `level`, `dailyGoal`, `theme`, `createdAt` |
| `progress` | SRS state per user per word | `userId`, `wordId`, `ease`, `interval`, `reps`, `due`, `lastReviewed` (unique: userId+wordId) |
| `activity` | Daily activity for streaks and charts | `userId`, `date` (YYYY-MM-DD), `wordsLearned`, `lessonsDone`, `xp` |
| `badges` | Badge definitions (content) | `_id`, `title`, `description`, `icon`, `rule` |
| `userBadges` | Badges earned | `userId`, `badgeId`, `earnedAt` |
| `reminders` | Reminder settings | `userId`, `enabled`, `hour`, `minute`, `days[]` |
| `leaderboard` | Weekly XP ranking (computed) | `userId`, `weekStart`, `xp`, `rank` |

Indexes to create in Atlas:
- `progress`: unique compound `{ userId: 1, wordId: 1 }`, and `{ userId: 1, due: 1 }` for the review queue.
- `activity`: unique `{ userId: 1, date: 1 }`.
- `leaderboard`: `{ weekStart: 1, xp: -1 }`.
