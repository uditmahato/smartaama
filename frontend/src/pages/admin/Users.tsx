import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { useEffect, useState } from "react";
import { Alert, Box, Button, Chip, Snackbar } from "@mui/material";
import {
  deleteUser,
  fetchAdminUsers,
  getErrorMessage,
  type UserOut,
} from "../../services/api";
import { useUser } from "../../hooks/useUser";
import Navbar, { navLinks } from "../../components/Navbar";
import IdCardDialog from "../../components/IdCardDialog";

export default function Users() {
  const { user: me } = useUser();
  const [rows, setRows] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [idCardUserId, setIdCardUserId] = useState<string | null>(null);

  // Load users from backend
  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await fetchAdminUsers());
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load users"));
    } finally {
      setLoading(false);
    }
  }

  // Delete (soft-delete) user
  async function remove(target: UserOut) {
    if (
      !window.confirm(
        `Deactivate user "${target.username}"? They will no longer be able to sign in.`,
      )
    )
      return;
    setBusyId(target.id);
    setError(null);
    try {
      await deleteUser(target.id);
      setNotice(`User "${target.username}" deactivated.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to delete user"));
    } finally {
      setBusyId(null);
    }
  }

  useEffect(() => {
    load();
  }, []);

  // Define table columns
  const columns: GridColDef<UserOut>[] = [
    { field: "username", headerName: "Username", flex: 1 },
    { field: "email", headerName: "Email", flex: 1 },
    { field: "full_name", headerName: "Name", flex: 1 },
    { field: "role", headerName: "Role", width: 120 },
    { field: "facility_type", headerName: "Facility", width: 110 },
    { field: "facility_name", headerName: "Facility Name", flex: 1 },
    { field: "nmc_number", headerName: "NMC Number", width: 130 },
    {
      field: "is_approved",
      headerName: "Status",
      width: 120,
      renderCell: (params) =>
        params.row.is_approved ? (
          <Chip label="Approved" color="success" size="small" />
        ) : (
          <Chip label="Pending" color="warning" size="small" />
        ),
    },
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
      width: 140,
      sortable: false,
      renderCell: (params) => (
        <Button
          color="error"
          size="small"
          variant="contained"
          onClick={() => remove(params.row)}
          disabled={busyId === params.row.id || params.row.id === me?.id}
        >
          Delete
        </Button>
      ),
    },
  ];

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#F6F7FB", py: 3, px: 2 }}>
      <Navbar
        title="Users"
        subtitle="Approved users — deactivate accounts or view ID cards"
        links={navLinks}
      />

      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <div style={{ height: 600, padding: 3 }}>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50, 100]} // include 100 to avoid MUI warning
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
