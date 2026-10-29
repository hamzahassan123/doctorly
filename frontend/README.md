# Doctorly frontend

Vite + React + TypeScript frontend for the Doctorly API. It uses Tailwind CSS,
TanStack Query, and React Router. All application data comes from the API at
`http://localhost:8000`; the frontend does not contain mock records.

## Run locally

From the `frontend/` directory:

```sh
npm install
npm run dev
```

Open `http://localhost:5173`. The Doctorly API must be reachable at
`http://localhost:8000`, and its CORS configuration must allow that origin.

Build a production bundle with `npm run build`.

## Features

- Patient registration and login with bearer-token storage in `localStorage`.
- Patient support chat streaming from `POST /chat`. Incremental `token` SSE
  events are rendered as they arrive; completed `message` events are also
  supported.
- Appointment availability, booking, and the authenticated patient's own
  appointment list.
- Staff-only dashboard for viewing, flagging, and cancelling appointments.
