const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.env.PORT) || 3000;
const rootDir = __dirname;
const cleanDir = path.join(rootDir, "data_modified_clean");
const dirtyDir = path.join(rootDir, "data_modified_dirty");

function readJson(dir, name) {
  return JSON.parse(fs.readFileSync(path.join(dir, name), "utf8"));
}

const TEXT_FILTERS = [
  "player_id",
  "session_id",
  "position_group",
  "playing_position",
  "acquisition_day",
  "training_model_name",
  "device_id",
];

function fail(res, status, message) {
  res.status(status).json({ error: message });
}

function wholeNumber(value, name) {
  if (value === undefined) {
    return undefined;
  }
  if (!/^\d+$/.test(value)) {
    const error = new Error(`${name} must be a whole number`);
    error.status = 400;
    throw error;
  }
  return Number(value);
}

function normalise(value) {
  return String(value).trim().toLowerCase().replace(/[\s_]+/g, "-");
}

function positionGroup(value) {
  const text = normalise(value);
  if (text === "forward" || text === "forwards") {
    return "forward";
  }
  if (text === "back" || text === "backs") {
    return "back";
  }
  return text;
}

function sameText(recordValue, queryValue, field) {
  const left = field === "position_group" ? positionGroup(recordValue) : normalise(recordValue);
  const right = field === "position_group" ? positionGroup(queryValue) : normalise(queryValue);
  return left === right;
}

function filteredSessions(sessions, query) {
  const trainingModel = wholeNumber(query.training_model, "training_model");
  const week = wholeNumber(query.week, "week");
  const jersey = wholeNumber(query.jersey_number, "jersey_number");

  return sessions.filter((record) => {
    for (const field of TEXT_FILTERS) {
      if (query[field] !== undefined && !sameText(record[field], query[field], field)) {
        return false;
      }
    }
    if (trainingModel !== undefined && record.training_model !== trainingModel) {
      return false;
    }
    if (week !== undefined && record.week !== week) {
      return false;
    }
    if (jersey !== undefined && record.jersey_number !== jersey) {
      return false;
    }
    if (query.date !== undefined && record.session_date !== query.date) {
      return false;
    }
    if (query.date_from !== undefined && record.session_date < query.date_from) {
      return false;
    }
    if (query.date_to !== undefined && record.session_date > query.date_to) {
      return false;
    }
    return true;
  });
}

function mountApi(app, base, dataset) {
  const { players, sessions, meta, integrity } = dataset;
  const playersById = new Map(players.map((player) => [player.player_id, player]));
  const api = `${base}/api`;
  const label = base === "" ? "trusted" : "untrusted";

  app.get(base || "/", (_req, res) => {
    res.json({
      name: `${meta.team} training API`,
      dataset: label,
      description: meta.warning || "Session workload records for a fictional school rugby squad. Measurements come from a published GPS study. Names, dates and devices are fictional.",
      endpoints: {
        meta: `${api}/meta`,
        players: `${api}/players`,
        player: `${api}/players/PLAYER_01`,
        sessions: `${api}/sessions?player_id=PLAYER_01&limit=5`,
        session: `${api}/sessions/REC_0001`,
        integrity: `${api}/integrity`,
        integrityRecord: `${api}/integrity/REC_0001`,
      },
      files: base === "/dirty"
        ? {
            players: "/dirty/players.csv",
            sessions: "/dirty/sessions.csv",
            integrity: "/dirty/integrity.csv",
            integrityFields: "/dirty/integrity_fields.csv",
          }
        : undefined,
    });
  });

  app.get(`${api}/meta`, (_req, res) => {
    res.json(meta);
  });

  app.get(`${api}/players`, (req, res) => {
    try {
      const group = req.query.position_group;
      const position = req.query.playing_position;
      const results = players.filter((player) => {
        if (group !== undefined && !sameText(player.position_group, group, "position_group")) {
          return false;
        }
        if (position !== undefined && !sameText(player.playing_position, position, "playing_position")) {
          return false;
        }
        return true;
      });
      res.json({ total: results.length, results });
    } catch (error) {
      fail(res, error.status || 500, error.message);
    }
  });

  app.get(`${api}/players/:playerId`, (req, res) => {
    const player = playersById.get(req.params.playerId.toUpperCase());
    if (!player) {
      fail(res, 404, "Player not found");
      return;
    }
    const playerSessions = sessions.filter((record) => record.player_id === player.player_id);
    res.json({ ...player, sessions: playerSessions.length });
  });

  app.get(`${api}/integrity/:recordId`, (req, res) => {
    const recordId = req.params.recordId.toUpperCase();
    const row = integrity.results.find((item) => item.record_id === recordId);
    if (!row) {
      fail(res, 404, "Integrity record not found");
      return;
    }
    res.json(row);
  });

  app.get(`${api}/integrity`, (req, res) => {
    try {
      let results = integrity.results;
      if (req.query.record_id !== undefined) {
        const recordId = String(req.query.record_id).toUpperCase();
        results = results.filter((item) => item.record_id === recordId);
      }
      const requestedPage = wholeNumber(req.query.page, "page");
      const requestedLimit = wholeNumber(req.query.limit, "limit");
      const page = requestedPage === undefined ? 1 : requestedPage;
      const limit = requestedLimit === undefined ? results.length || 1 : requestedLimit;
      if (page < 1) {
        fail(res, 400, "page must be 1 or more");
        return;
      }
      if (limit < 1 || limit > integrity.results.length) {
        fail(res, 400, `limit must be from 1 to ${integrity.results.length}`);
        return;
      }
      const start = (page - 1) * limit;
      res.json({
        algorithm: integrity.algorithm,
        encoding: integrity.encoding,
        digest: integrity.digest,
        separator: integrity.separator,
        missing_value: integrity.missing_value,
        identity_fields: integrity.identity_fields,
        performance_fields: integrity.performance_fields,
        all_data_fields: integrity.all_data_fields,
        field_hash_fields: integrity.field_hash_fields,
        how_to_hash: integrity.how_to_hash,
        how_to_hash_field: integrity.how_to_hash_field,
        example: integrity.example,
        page,
        limit,
        total: results.length,
        pages: Math.ceil(results.length / limit) || 0,
        results: results.slice(start, start + limit),
      });
    } catch (error) {
      fail(res, error.status || 500, error.message);
    }
  });

  app.get(`${api}/sessions/:recordId`, (req, res) => {
    const recordId = req.params.recordId.toUpperCase();
    if (recordId.startsWith("SESSION_")) {
      fail(res, 400, `Use ${api}/sessions?session_id=SESSION_001 to list a session`);
      return;
    }
    const record = sessions.find((item) => item.record_id === recordId);
    if (!record) {
      fail(res, 404, "Record not found");
      return;
    }
    res.json(record);
  });

  app.get(`${api}/sessions`, (req, res) => {
    try {
      const requestedPage = wholeNumber(req.query.page, "page");
      const requestedLimit = wholeNumber(req.query.limit, "limit");
      const page = requestedPage === undefined ? 1 : requestedPage;
      const limit = requestedLimit === undefined ? 50 : requestedLimit;
      if (page < 1) {
        fail(res, 400, "page must be 1 or more");
        return;
      }
      if (limit < 1 || limit > sessions.length) {
        fail(res, 400, `limit must be from 1 to ${sessions.length}`);
        return;
      }

      const matches = filteredSessions(sessions, req.query);
      const start = (page - 1) * limit;
      res.json({
        page,
        limit,
        total: matches.length,
        pages: Math.ceil(matches.length / limit) || 0,
        results: matches.slice(start, start + limit),
      });
    } catch (error) {
      fail(res, error.status || 500, error.message);
    }
  });
}

const cleanIntegrity = readJson(cleanDir, "integrity.json");
const cleanMeta = readJson(cleanDir, "meta.json");
cleanMeta.hash = {
  algorithm: cleanIntegrity.algorithm,
  encoding: cleanIntegrity.encoding,
  digest: cleanIntegrity.digest,
  separator: cleanIntegrity.separator,
  missing_value: cleanIntegrity.missing_value,
  identity_fields: cleanIntegrity.identity_fields,
  performance_fields: cleanIntegrity.performance_fields,
  all_data_fields: cleanIntegrity.all_data_fields,
  field_hash_fields: cleanIntegrity.field_hash_fields,
  how_to_hash: cleanIntegrity.how_to_hash,
  how_to_hash_field: cleanIntegrity.how_to_hash_field,
  example: cleanIntegrity.example,
};

const app = express();
app.use(cors());

mountApi(app, "", {
  players: readJson(cleanDir, "players.json"),
  sessions: readJson(cleanDir, "sessions.json"),
  meta: cleanMeta,
  integrity: cleanIntegrity,
});

mountApi(app, "/dirty", {
  players: readJson(dirtyDir, "players.json"),
  sessions: readJson(dirtyDir, "sessions.json"),
  meta: readJson(dirtyDir, "meta.json"),
  integrity: readJson(dirtyDir, "integrity.json"),
});

app.get("/dirty/players.csv", (_req, res) => {
  res.sendFile(path.join(dirtyDir, "players.csv"));
});
app.get("/dirty/sessions.csv", (_req, res) => {
  res.sendFile(path.join(dirtyDir, "sessions.csv"));
});
app.get("/dirty/integrity.csv", (_req, res) => {
  res.sendFile(path.join(dirtyDir, "integrity.csv"));
});
app.get("/dirty/integrity_fields.csv", (_req, res) => {
  res.sendFile(path.join(dirtyDir, "integrity_fields.csv"));
});

app.use((req, res) => {
  fail(res, 404, `No route for ${req.method} ${req.path}`);
});

app.listen(PORT, () => {
  console.log(`Training API listening on http://localhost:${PORT}`);
  console.log(`Untrusted feed: http://localhost:${PORT}/dirty`);
});
