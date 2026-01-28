import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { Box, Button, Stack, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { api } from "../../services/api";
import Navbar, { navLinks } from "../../components/Navbar";

type User = {
  id: string;
  full_name: string;
  email: string;
  phone_number: string;
  facility_type: string;
  working_hospital: string;
  created_at: string;
};

export default function PendingUsers() {
  const [rows, setRows] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const res = await api.get("/admin/users/pending");
    setRows(res.data);
    setLoading(false);
  }

  async function approve(id: string) {
    await api.patch(`/admin/users/${id}/approve`);
    load();
  }

  async function reject(id: string) {
    await api.patch(`/admin/users/${id}/reject`);
    load();
  }

  useEffect(() => {
    load();
  }, []);

  const columns: GridColDef[] = [
    { field: "full_name", headerName: "Name", flex: 1 },
    { field: "email", headerName: "Email", flex: 1 },
    { field: "phone_number", headerName: "Phone", flex: 1 },
    { field: "facility_type", headerName: "Facility", width: 120 },
    { field: "working_hospital", headerName: "Hospital", flex: 1 },
    {
      field: "created_at",
      headerName: "Registered At",
      width: 180,
      valueFormatter: ({ value }) =>
        value ? new Date(value as string).toLocaleString() : "-",
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
            onClick={() => approve(params.row.id)}
          >
            Approve
          </Button>
          <Button
            color="error"
            size="small"
            variant="contained"
            onClick={() => reject(params.row.id)}
          >
            Reject
          </Button>
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

      <div style={{ height: 600, padding: 3 }}>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50]}
          disableRowSelectionOnClick
        />
      </div>
    </Box>
  );
}
