import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import {
  Alert,
  Box,
  Button,
  Snackbar,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";
import {
  approveUser,
  fetchPendingUsers,
  fetchRejectedUsers,
  getErrorMessage,
  rejectUser,
  type UserOut,
} from "../../services/api";
import Navbar, { navLinks } from "../../components/Navbar";
import IdCardDialog from "../../components/IdCardDialog";

/** Which registrations the grid shows: awaiting approval, or rejected (re-approvable). */
type View = "pending" | "rejected";

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export default function PendingUsers() {
  const [view, setView] = useState<View>("pending");
  const [rows, setRows] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [idCardUserId, setIdCardUserId] = useState<string | null>(null);

  // Load the current view (pending or rejected users)
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(
        view === "pending"
          ? await fetchPendingUsers()
          : await fetchRejectedUsers(),
      );
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          view === "pending"
            ? "Failed to load pending users"
            : "Failed to load rejected users",
        ),
      );
    } finally {
      setLoading(false);
    }
  }, [view]);

  async function approve(target: UserOut) {
    setBusyId(target.id);
    setError(null);
    try {
      await approveUser(target.id);
      setNotice(`Approved ${target.full_name || target.username}.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to approve user"));
    } finally {
      setBusyId(null);
    }
  }

  async function reject(target: UserOut) {
    if (
      !window.confirm(
        `Reject registration for ${target.full_name || target.username}?`,
      )
    )
      return;
    setBusyId(target.id);
    setError(null);
    try {
      await rejectUser(target.id);
      setNotice(`Rejected ${target.full_name || target.username}.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to reject user"));
    } finally {
      setBusyId(null);
    }
  }

  useEffect(() => {
    load();
  }, [load]);

  const columns: GridColDef<UserOut>[] = [
    { field: "full_name", headerName: "Name", flex: 1 },
    { field: "email", headerName: "Email", flex: 1 },
    { field: "phone_number", headerName: "Phone", width: 140 },
    { field: "facility_type", headerName: "Facility", width: 110 },
    { field: "facility_name", headerName: "Facility Name", flex: 1 },
    { field: "working_hospital", headerName: "Working Hospital", flex: 1 },
    { field: "nmc_number", headerName: "NMC Number", width: 130 },
    ...(view === "rejected"
      ? ([
          {
            field: "rejected_at",
            headerName: "Rejected At",
            width: 170,
            valueGetter: (_value, row) => formatDateTime(row.rejected_at),
          },
        ] as GridColDef<UserOut>[])
      : []),
    {
      field: "id_card",
      headerName: "ID Card",
      width: 110,
      sortable: false,
      renderCell: (params) =>
        params.row.has_id_card ? (
          <Button
            size="small"
            variant="outlined"
            onClick={() => setIdCardUserId(params.row.id)}
          >
            View
          </Button>
        ) : (
          <span style={{ color: "rgba(0,0,0,0.38)" }}>None</span>
        ),
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 200,
      sortable: false,
      renderCell: (params) => (
        <Stack direction="row" spacing={1}>
          <Button
            color="success"
            size="small"
            variant="contained"
            onClick={() => approve(params.row)}
            disabled={busyId === params.row.id}
          >
            Approve
          </Button>
          {view === "pending" && (
            <Button
              color="error"
              size="small"
              variant="contained"
              onClick={() => reject(params.row)}
              disabled={busyId === params.row.id}
            >
              Reject
            </Button>
          )}
        </Stack>
      ),
    },
  ];

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#F6F7FB",
        py: { xs: 2, md: 3 },
        px: { xs: 0.5, sm: 1, md: 1.5 },
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      <Navbar
        title="Pending Users"
        subtitle="Manage users who have not yet been approved"
        links={navLinks}
      />

      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Stack
        direction="row"
        spacing={2}
        alignItems="center"
        sx={{ mt: 2, mb: 1, px: 0.5 }}
      >
        <ToggleButtonGroup
          value={view}
          exclusive
          size="small"
          color="primary"
          aria-label="Registration list"
          onChange={(_e, next: View | null) => {
            if (next) setView(next);
          }}
        >
          <ToggleButton value="pending">Pending</ToggleButton>
          <ToggleButton value="rejected">Rejected</ToggleButton>
        </ToggleButtonGroup>
        <Typography variant="body2" color="text.secondary">
          {view === "pending"
            ? "Registrations awaiting a decision."
            : "Rejected registrations — Approve re-admits the account."}
        </Typography>
      </Stack>

      <div style={{ height: 600, padding: 3 }}>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50, 100]}
          disableRowSelectionOnClick
        />
      </div>

      <IdCardDialog
        userId={idCardUserId}
        onClose={() => setIdCardUserId(null)}
      />

      <Snackbar
        open={Boolean(notice)}
        autoHideDuration={4000}
        onClose={() => setNotice(null)}
        message={notice ?? ""}
      />
    </Box>
  );
}
