CREATE TRIGGER t_server_audit_stamp_b_iu
       BEFORE INSERT OR UPDATE
    ON ele_server
   FOR EACH ROW
       EXECUTE PROCEDURE sp_audit_stamps();
