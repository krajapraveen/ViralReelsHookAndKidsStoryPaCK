package com.creatorstudio.repository;

import com.creatorstudio.entity.Generation;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface GenerationRepository extends JpaRepository<Generation, UUID> {
    Page<Generation> findByUserIdOrderByCreatedAtDesc(UUID userId, Pageable pageable);
    Page<Generation> findByUserIdAndTypeOrderByCreatedAtDesc(UUID userId, Generation.Type type, Pageable pageable);
}